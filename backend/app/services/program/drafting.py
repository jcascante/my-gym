from typing import Any

from app.models import Exercise, ProgramStatus, ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.models.exercise import Muscle
from app.schemas.program import EffortMethod
from app.schemas.program_api import Advisory
from app.schemas.template import SchemeDef, SlotRule, TemplateDefinition
from app.services.program.adaptation import _reselect
from app.services.program.assembly import SlotAssignment, assemble_session
from app.services.program.engine_config import EngineConfig
from app.services.program.ledger import LedgerPick, band_for_experience, compute_ledger
from app.services.program.selection import SelectionContext, _extract_features, ranked_pool_for_slot
from app.services.program.taxonomy import ROLE_FACTOR, muscle_group_for
from app.services.program.variety import pool_size_for, rotation_pool_ids


def _base_load_for(
    rule: SlotRule, scheme: SchemeDef, applies_to_values: dict[str, float], effort_method: str | None
) -> float | None:
    value = applies_to_values.get(rule.pattern) if rule.pattern else None
    if value is None and rule.region:
        value = applies_to_values.get(rule.region)
    if value is None:
        return None
    if effort_method == EffortMethod.PERCENT_1RM.value and scheme.intensity_pct is not None:
        return round(float(value) * scheme.intensity_pct, 2)
    return float(value)


def _make_workout_exercise(
    order: int,
    chosen: Exercise,
    rule: SlotRule,
    scheme: SchemeDef,
    ranked: list[Exercise],
    pool_size: int,
    applies_to_values: dict[str, float],
    effort_method: str | None,
) -> WorkoutExercise:
    return WorkoutExercise(
        order=order,
        exercise_id=chosen.id,
        fills_rule=rule.model_dump(),
        sets=scheme.sets,
        reps_min=scheme.reps_min,
        reps_max=scheme.reps_max,
        base_load=_base_load_for(rule, scheme, applies_to_values, effort_method),
        rest_seconds=scheme.rest_seconds,
        scheme_key=rule.scheme,
        target_rpe=scheme.target_rpe,
        intensity_pct=scheme.intensity_pct,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=rotation_pool_ids(ranked, pool_size),
    )


def _apply_pick_to_ctx(ctx: SelectionContext, chosen: Exercise, *, sets: int, is_hard: bool, workout_key: str) -> None:
    ctx.used_movement_slugs.add(chosen.movement_slug)
    ctx.used_unilateral_flags.append(chosen.is_unilateral)
    for muscle in chosen.primary_muscles:
        ctx.muscle_coverage[muscle] += 1
    ctx.ledger.apply(LedgerPick(exercise_id=chosen.id, workout_key=workout_key, sets=sets, is_hard=is_hard), chosen)


def build_draft(
    template: ProgramTemplate,
    definition: TemplateDefinition,
    ctx: SelectionContext,
    exercises: list[Exercise],
    *,
    user_id: int,
    environment_id: int,
    days_per_week: int,
    duration_weeks: int,
    weight_unit: str,
    required_inputs: dict[str, float],
    progression_style: str = "consistent",
    effort_method: str | None = None,
    variety_preference: str = "low",
    engine_config_version: str = "unversioned",
    config: EngineConfig | None = None,
    telemetry_sink: list[dict[str, Any]] | None = None,
    advisory_sink: list[Advisory] | None = None,
) -> WorkoutProgram:
    applies_to_values = {
        ri.applies_to: required_inputs[ri.key]
        for ri in definition.required_inputs
        if ri.applies_to and ri.key in required_inputs
    }
    program = WorkoutProgram(
        user_id=user_id,
        template_id=template.id,
        environment_id=environment_id,
        name=template.name,
        focus=(template.goals[0] if template.goals else None),
        status=ProgramStatus.DRAFT,
        duration_weeks=duration_weeks,
        days_per_week=days_per_week,
        weight_unit=weight_unit,
        constraints={
            "locked_slots": [],
            "excluded_exercise_ids": [],
            "swaps": {},
            "volume_adjustments": {},
            "required_inputs": required_inputs,
            "progression_style": progression_style,
            "effort_method": effort_method,
            "movement_preferences": ctx.movement_preferences,
            "complementary_focus": ctx.complementary_focus,
            "variety_preference": variety_preference,
            "engine_config_version": engine_config_version,
        },
    )
    use_beam = config is not None and config.flags.use_beam_search
    for session in definition.split.sessions:
        workout = Workout(
            key=session.key,
            name=session.name,
            focus=",".join(filter(None, [s.pattern or s.region for s in session.slots])),
            order=session.order,
        )
        if use_beam:
            assert config is not None  # narrowed by use_beam
            assignments: list[SlotAssignment] = assemble_session(
                session.slots,
                exercises,
                ctx,
                config.assembly.beam_width,
                config=config,
                schemes=definition.schemes,
                workout_key=session.key,
            )
            for a in assignments:
                scheme = definition.schemes[a.rule.scheme]
                pool_size = 1 if a.rule.priority == "primary" else pool_size_for(variety_preference)
                if telemetry_sink is not None:
                    telemetry_sink.append(
                        {
                            "workout_key": session.key,
                            "order": a.order,
                            "exercise_id": a.exercise.id,
                            "features": _extract_features(a.exercise, a.rule, ctx),
                        }
                    )
                # Apply the winning beam's picks to the shared ctx in slot order, so the next
                # session continues from the correct accumulated variety/coverage/ledger state.
                _apply_pick_to_ctx(
                    ctx, a.exercise, sets=scheme.sets, is_hard=(a.rule.scheme == "main"), workout_key=session.key
                )
                workout.exercises.append(
                    _make_workout_exercise(
                        a.order,
                        a.exercise,
                        a.rule,
                        scheme,
                        a.ranked_candidates,
                        pool_size,
                        applies_to_values,
                        effort_method,
                    )
                )
        else:
            for i, rule in enumerate(session.slots, start=1):
                scheme = definition.schemes[rule.scheme]
                ranked = ranked_pool_for_slot(exercises, rule, ctx, set())
                chosen = ranked[0] if ranked else None
                if chosen is None:
                    continue
                pool_size = 1 if rule.priority == "primary" else pool_size_for(variety_preference)
                if telemetry_sink is not None:
                    telemetry_sink.append(
                        {
                            "workout_key": session.key,
                            "order": i,
                            "exercise_id": chosen.id,
                            "features": _extract_features(chosen, rule, ctx),
                        }
                    )
                _apply_pick_to_ctx(
                    ctx, chosen, sets=scheme.sets, is_hard=(rule.scheme == "main"), workout_key=session.key
                )
                workout.exercises.append(
                    _make_workout_exercise(i, chosen, rule, scheme, ranked, pool_size, applies_to_values, effort_method)
                )
        program.workouts.append(workout)

    # The post-draft volume validator is gated on its own dedicated flag,
    # `flags.use_volume_validator` -- not on `lambda_v`/`lambda_f`, and not merely
    # `config is not None`. Those lambdas are beam-search assembly-objective scoring
    # weights (see `AssemblyConfig`'s docstring); the validator is a separate, mutating
    # mechanism (post-draft `_reselect` calls) that also runs on the greedy path, so
    # coupling it to lambda would let anyone experimenting with assembly scoring
    # silently enable mutating re-selection they never asked for. Gating on bare
    # `config is not None` was tried first and rejected: the sample exercise catalog +
    # templates leave most muscle groups genuinely below MEV for a typical short split,
    # so the validator would fire -- and mutate the draft via `_reselect` -- for existing
    # regression tests that pass a config expecting byte-identical output vs.
    # `config=None` (`test_config_with_flag_off_matches_config_none`,
    # `test_beam_width_1_reproduces_greedy_output_exactly`, and the harness's
    # width=1-equivalence sweep across ~250 profiles), none of which set
    # `use_volume_validator=True`. See task-2.5a-report.md for the full reasoning.
    if config is not None and config.flags.use_volume_validator:
        _validate_and_repair_volume(program, definition, ctx, exercises, config, advisory_sink)

    # Independent post-draft pass, gated on its own dedicated flag (never reused from an
    # unrelated field, per the established Task 2.5a convention). Safe to run after the
    # volume validator: that pass only swaps `exercise_id` via `_reselect` (never touches
    # `.order` or slot count); this pass only reorders existing rows and renumbers
    # `.order` (never changes which exercise is picked or how many sets) -- the two
    # commute.
    if config is not None and config.flags.use_interference_scheduler:
        _apply_interference_scheduling(program, exercises, advisory_sink)
    return program


def _group_contribution(exercise: Exercise, group: str, sets: int) -> float:
    """How much a single WorkoutExercise row (for `exercise`, with `sets` sets) credits
    `group`'s effective weekly sets -- mirrors `ledger.py`'s primary/secondary
    group-crediting + role-factor logic for a single pick, without needing a full
    `LedgerAccumulator` round-trip."""
    primary_groups = {g for m in exercise.primary_muscles if (g := muscle_group_for(Muscle(m))) is not None}
    if group in primary_groups:
        return sets * ROLE_FACTOR["primary"]
    secondary_groups = {
        g for m in exercise.secondary_muscles if (g := muscle_group_for(Muscle(m))) is not None
    } - primary_groups
    if group in secondary_groups:
        return sets * ROLE_FACTOR["secondary"]
    return 0.0


def _validate_and_repair_volume(
    program: WorkoutProgram,
    definition: TemplateDefinition,  # noqa: ARG001 -- unused today; reserved for template-structure-aware repair (Task 2.5b territory)
    ctx: SelectionContext,
    exercises: list[Exercise],
    config: EngineConfig,
    advisory_sink: list[Advisory] | None,
) -> None:
    """Post-draft volume validation + best-effort repair (plan §2.5, proposal §4.3).

    One bounded pass: every group violating MEV/MRV gets exactly one targeted
    `_reselect` attempt on its least-/most-contributing non-locked slot, then the ledger
    is recomputed once and any group still violating gets a structured `Advisory`.

    Not a loop-until-resolved: `_reselect` reuses the ordinary, ledger-unaware
    `select_for_slot` heuristic -- it has no way to bias its pick toward improving a
    specific muscle group, so there's no guarantee retrying would ever converge.
    Surfacing what didn't resolve via an `Advisory` (rather than pretending a loop would
    reliably fix it) matches the proposal's own framing: "surfaced, not silently
    accepted." Making `_reselect` ledger-aware is a natural follow-up, out of scope here.
    """
    exercise_by_id = {ex.id: ex for ex in exercises}
    band = band_for_experience(config.volume_bands, ctx.experience)

    ledger = compute_ledger(program, exercises)
    violations = [
        group
        for group, gl in ledger.items()
        if gl.effective_sets_week < band.mev or gl.effective_sets_week > band.mrv_guard
    ]

    rows: list[tuple[Workout, WorkoutExercise]] = [(w, we) for w in program.workouts for we in w.exercises]

    for group in violations:
        below = ledger[group].effective_sets_week < band.mev
        candidates = [(w, we) for w, we in rows if not we.is_locked]
        if not candidates:
            continue

        def _contribution(item: tuple[Workout, WorkoutExercise]) -> float:
            w, we = item
            ex = exercise_by_id.get(we.exercise_id)
            return 0.0 if ex is None else _group_contribution(ex, group, we.sets)

        if below:
            target = min(candidates, key=lambda item: (_contribution(item), item[0].order, item[1].order))
        else:
            target = min(candidates, key=lambda item: (-_contribution(item), item[0].order, item[1].order))
        _reselect(program, target[1].id, ctx, exercises)

    ledger = compute_ledger(program, exercises)
    if advisory_sink is None:
        return
    for group, gl in ledger.items():
        label = group.replace("_", " ").title()
        if gl.effective_sets_week < band.mev:
            advisory_sink.append(
                Advisory(
                    code="VOLUME_BELOW_MEV",
                    severity="warning",
                    subject=group,
                    message=(
                        f"{label} receives {gl.effective_sets_week:.1f} effective sets this week, "
                        f"below the {band.mev}-set minimum for your level."
                    ),
                )
            )
        elif gl.effective_sets_week > band.mrv_guard:
            advisory_sink.append(
                Advisory(
                    code="VOLUME_ABOVE_MRV",
                    severity="warning",
                    subject=group,
                    message=(
                        f"{label} receives {gl.effective_sets_week:.1f} effective sets this week, "
                        f"above the {band.mrv_guard}-set maximum for your level."
                    ),
                )
            )


_LOWER_BODY_STRENGTH_PATTERNS = {"squat", "hinge", "lunge"}


def _is_heavy_lower_body_strength(we: WorkoutExercise) -> bool:
    return we.fills_rule.get("pattern") in _LOWER_BODY_STRENGTH_PATTERNS and we.fills_rule.get("priority") == "primary"


def _is_conditioning(we: WorkoutExercise, exercise_by_id: dict[int, Exercise]) -> bool:
    exercise = exercise_by_id.get(we.exercise_id)
    return exercise is not None and Muscle.CARDIO.value in exercise.primary_muscles


def _apply_interference_scheduling(
    program: WorkoutProgram, exercises: list[Exercise], advisory_sink: list[Advisory] | None
) -> None:
    """Post-draft interference scheduling: strength-before-conditioning same-day
    placement + separation advisory (plan §2.7, proposal §4.5 bullets 1-2).

    Deliberate scope reduction (see task-2.7b-brief.md): the proposal's bullet 2
    distinguishes high- from low-intensity conditioning work (only the former needs the
    separation constraint). No data field in this schema carries an intensity/effort
    signal for any exercise, so this pass applies the rule uniformly to every
    cardio-primary-muscle slot rather than inventing an unsourced classification (e.g.
    keyword-matching exercise names). A natural extension once the exercise schema grows
    an intensity/effort tag.
    """
    exercise_by_id = {ex.id: ex for ex in exercises}
    for workout in program.workouts:
        has_strength = any(_is_heavy_lower_body_strength(we) for we in workout.exercises)
        has_conditioning = any(_is_conditioning(we, exercise_by_id) for we in workout.exercises)
        if not (has_strength and has_conditioning):
            continue
        workout.exercises.sort(key=lambda we: _is_conditioning(we, exercise_by_id))
        for position, we in enumerate(workout.exercises, start=1):
            we.order = position
        if advisory_sink is not None:
            advisory_sink.append(
                Advisory(
                    code="CONDITIONING_SEPARATION_RECOMMENDED",
                    severity="info",
                    subject=workout.key,
                    message=(
                        f"{workout.name} includes both heavy lower-body strength and conditioning work. "
                        f"Where possible, separate these by at least 6 hours (e.g., strength earlier in the "
                        f"day, conditioning later) to reduce interference with your strength adaptations."
                    ),
                )
            )
