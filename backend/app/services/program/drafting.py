from typing import Any

from app.models import Exercise, ProgramStatus, ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.program import EffortMethod
from app.schemas.template import SchemeDef, SlotRule, TemplateDefinition
from app.services.program.assembly import SlotAssignment, assemble_session
from app.services.program.engine_config import EngineConfig
from app.services.program.selection import SelectionContext, _extract_features, ranked_pool_for_slot
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


def _apply_pick_to_ctx(ctx: SelectionContext, chosen: Exercise) -> None:
    ctx.used_movement_slugs.add(chosen.movement_slug)
    ctx.used_unilateral_flags.append(chosen.is_unilateral)
    for muscle in chosen.primary_muscles:
        ctx.muscle_coverage[muscle] += 1


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
                session.slots, exercises, ctx, config.assembly.beam_width
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
                # session continues from the correct accumulated variety/coverage state.
                _apply_pick_to_ctx(ctx, a.exercise)
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
                _apply_pick_to_ctx(ctx, chosen)
                workout.exercises.append(
                    _make_workout_exercise(i, chosen, rule, scheme, ranked, pool_size, applies_to_values, effort_method)
                )
        program.workouts.append(workout)
    return program
