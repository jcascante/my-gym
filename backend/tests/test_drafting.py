import pytest

from app.models.exercise import BodyRegion, Exercise, ExperienceLevel, MovementPattern
from app.models.program import ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.template import ProgressionRef, SchemeDef, SessionDef, SlotRule, SplitDef, TemplateDefinition
from app.services.program.drafting import (
    _apply_interference_scheduling,
    _apply_safety_substitution,
    _validate_and_repair_volume,
    build_draft,
)
from app.services.program.engine_config import AssemblyConfig, EngineConfig, EngineFlags
from app.services.program.ledger import compute_ledger
from app.services.program.regression_graphs import RegressionEdge, RegressionGraphsConfig
from app.services.program.selection import ActiveInjuryProvocation, SelectionContext, SelectionWeights
from app.services.program.taxonomy import MUSCLE_GROUPS

FEATURE_KEYS = {
    "variety",
    "priority_fit",
    "muscle_fit",
    "difficulty",
    "unilateral_balance",
    "movement_preference",
    "complementary_coverage",
}


def _ctx():
    return SelectionContext(
        equipment=["barbell", "bench", "squat_rack", "none"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
    )


def _build(ctx, template, definition, exercises, config=None):
    return build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        config=config,
    )


def _fingerprint(program):
    return [
        [(ex.order, ex.exercise_id, ex.scheme_key, ex.base_load, tuple(ex.rotation_pool)) for ex in w.exercises]
        for w in program.workouts
    ]


@pytest.mark.asyncio
async def test_beam_width_1_reproduces_greedy_output_exactly(sample_template_orm, sample_exercises):
    """width=1 beam search must yield a byte-identical program to the greedy path."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    greedy = _build(_ctx(), sample_template_orm, definition, sample_exercises, config=None)
    config = EngineConfig(
        config_version="test",
        assembly=AssemblyConfig(beam_width=1),
        flags=EngineFlags(use_beam_search=True),
    )
    beam = _build(_ctx(), sample_template_orm, definition, sample_exercises, config=config)
    assert _fingerprint(beam) == _fingerprint(greedy)


@pytest.mark.asyncio
async def test_config_with_flag_off_matches_config_none(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    greedy = _build(_ctx(), sample_template_orm, definition, sample_exercises, config=None)
    config = EngineConfig(config_version="test", flags=EngineFlags(use_beam_search=False))
    off = _build(_ctx(), sample_template_orm, definition, sample_exercises, config=config)
    assert _fingerprint(off) == _fingerprint(greedy)


@pytest.mark.asyncio
async def test_build_draft_fills_slots(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert len(program.workouts) == len(definition.split.sessions)
    assert all(w.exercises for w in program.workouts)


@pytest.mark.asyncio
async def test_build_draft_links_required_input_via_applies_to(sample_template_orm, sample_exercises):
    """Regression: base_load must be seeded via RequiredInput.applies_to, not a pattern-prefix guess.

    The horizontal_push slot is seeded by "bench_start" (applies_to="horizontal_push"), which does
    NOT share a string prefix with "horizontal_push" - a naive prefix match would leave it None.
    """
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    horizontal_push_exercises = [
        ex for w in program.workouts for ex in w.exercises if ex.fills_rule.get("pattern") == "horizontal_push"
    ]
    assert horizontal_push_exercises
    assert all(ex.base_load == 60.0 for ex in horizontal_push_exercises)


@pytest.mark.asyncio
async def test_build_draft_stores_progression_style_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        progression_style="variable",
    )
    assert program.constraints["progression_style"] == "variable"


@pytest.mark.asyncio
async def test_build_draft_defaults_progression_style_to_consistent(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["progression_style"] == "consistent"


@pytest.mark.asyncio
async def test_build_draft_denormalizes_effort_targets_onto_workout_exercise(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    main_scheme_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"]
    assert main_scheme_exercises
    assert all(ex.target_rpe == 8.0 for ex in main_scheme_exercises)
    assert all(ex.intensity_pct == 0.8 for ex in main_scheme_exercises)


@pytest.mark.asyncio
async def test_build_draft_computes_percent_1rm_base_load(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 100, "bench_start": 60},
        effort_method="percent_1rm",
    )
    squat_exercises = [ex for w in program.workouts for ex in w.exercises if ex.fills_rule.get("pattern") == "squat"]
    main_squats = [ex for ex in squat_exercises if ex.scheme_key == "main"]
    assert main_squats
    assert all(ex.base_load == 80.0 for ex in main_squats)  # 100 * 0.8 intensity_pct


@pytest.mark.asyncio
async def test_build_draft_base_load_unaffected_when_effort_method_unset(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 100, "bench_start": 60},
    )
    squat_exercises = [
        ex
        for w in program.workouts
        for ex in w.exercises
        if ex.fills_rule.get("pattern") == "squat" and ex.scheme_key == "main"
    ]
    assert squat_exercises
    assert all(ex.base_load == 100.0 for ex in squat_exercises)  # unchanged, backward compatible


@pytest.mark.asyncio
async def test_build_draft_stores_movement_preferences_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
        movement_preferences={"kettlebell": 1.5},
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["movement_preferences"] == {"kettlebell": 1.5}


@pytest.mark.asyncio
async def test_build_draft_stores_complementary_focus_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
        complementary_focus=False,
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["complementary_focus"] is False


@pytest.mark.asyncio
async def test_build_draft_updates_muscle_coverage_after_each_pick(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
    )
    assert sum(ctx.muscle_coverage.values()) == 0
    build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert sum(ctx.muscle_coverage.values()) > 0  # at least one primary muscle was tallied


@pytest.mark.asyncio
async def test_build_draft_stores_engine_config_version_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        engine_config_version="1",
    )
    assert program.constraints["engine_config_version"] == "1"


@pytest.mark.asyncio
async def test_build_draft_defaults_engine_config_version_when_unspecified(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["engine_config_version"] == "unversioned"


@pytest.mark.asyncio
async def test_build_draft_primary_slots_get_single_entry_rotation_pool(sample_template_orm, sample_exercises):
    """Primary (scheme='main') slots never rotate, regardless of variety preference."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack", "none"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
    )
    main_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"]
    assert main_exercises
    for ex in main_exercises:
        assert ex.rotation_pool == [ex.exercise_id]


@pytest.mark.asyncio
async def test_build_draft_accessory_slots_sized_by_variety_preference(sample_template_orm, sample_exercises):
    """Accessory slots rotate; pool size follows the variety preference (high -> up to 3)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack", "none"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
    )
    accessory_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key == "accessory"]
    assert accessory_exercises
    assert all(len(ex.rotation_pool) == 3 for ex in accessory_exercises)


@pytest.mark.asyncio
async def test_build_draft_defaults_variety_preference_to_low(sample_template_orm, sample_exercises):
    """Without an explicit variety_preference, every slot (primary and accessory) gets pool size 1."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack", "none"],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["variety_preference"] == "low"
    all_exercises = [ex for w in program.workouts for ex in w.exercises]
    assert all_exercises
    assert all(len(ex.rotation_pool) == 1 for ex in all_exercises)


@pytest.mark.asyncio
async def test_build_draft_telemetry_sink_none_is_noop(sample_template_orm, sample_exercises):
    """Default telemetry_sink=None (every existing call site) must not change behavior."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    with_default = _build(_ctx(), sample_template_orm, definition, sample_exercises)
    explicit_none = build_draft(
        sample_template_orm,
        definition,
        _ctx(),
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        telemetry_sink=None,
    )
    assert _fingerprint(with_default) == _fingerprint(explicit_none)


@pytest.mark.asyncio
async def test_build_draft_greedy_telemetry_sink_records_one_entry_per_slot(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    sink: list[dict] = []
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        telemetry_sink=sink,
    )
    all_picked = [(w.key, ex.order, ex.exercise_id) for w in program.workouts for ex in w.exercises]
    assert len(sink) == len(all_picked)
    for entry, (workout_key, order, exercise_id) in zip(sink, all_picked):
        assert entry["workout_key"] == workout_key
        assert entry["order"] == order
        assert entry["exercise_id"] == exercise_id
        assert set(entry["features"].keys()) == FEATURE_KEYS


@pytest.mark.asyncio
async def test_build_draft_beam_telemetry_sink_records_one_entry_per_slot(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    sink: list[dict] = []
    config = EngineConfig(
        config_version="test",
        assembly=AssemblyConfig(beam_width=1),
        flags=EngineFlags(use_beam_search=True),
    )
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        config=config,
        telemetry_sink=sink,
    )
    all_picked = [(w.key, ex.order, ex.exercise_id) for w in program.workouts for ex in w.exercises]
    assert len(sink) == len(all_picked)
    for entry, (workout_key, order, exercise_id) in zip(sink, all_picked):
        assert entry["workout_key"] == workout_key
        assert entry["order"] == order
        assert entry["exercise_id"] == exercise_id
        assert set(entry["features"].keys()) == FEATURE_KEYS


@pytest.mark.asyncio
async def test_build_draft_telemetry_sink_does_not_affect_program_output(sample_template_orm, sample_exercises):
    """Passing a sink must not change the resulting program vs. telemetry_sink=None."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    without_sink = _build(_ctx(), sample_template_orm, definition, sample_exercises)
    sink: list[dict] = []
    with_sink = build_draft(
        sample_template_orm,
        definition,
        _ctx(),
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        telemetry_sink=sink,
    )
    assert _fingerprint(without_sink) == _fingerprint(with_sink)
    assert sink  # sanity: something was recorded


# --- ctx.ledger bookkeeping (decision #4/#7: unconditional, safe no-op) -----------


@pytest.mark.asyncio
async def test_build_draft_populates_ctx_ledger_greedy(sample_template_orm, sample_exercises):
    """_apply_pick_to_ctx's ledger.apply() call runs unconditionally (config=None too),
    so ctx.ledger must end up matching an independent compute_ledger() over the same
    program -- proving the bookkeeping is accurate, not just "doesn't crash"."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    program = _build(ctx, sample_template_orm, definition, sample_exercises, config=None)
    expected = compute_ledger(program, sample_exercises)
    actual = ctx.ledger.snapshot()
    for group in MUSCLE_GROUPS:
        assert actual[group].effective_sets_week == pytest.approx(expected[group].effective_sets_week)
        assert actual[group].frequency_days == expected[group].frequency_days


@pytest.mark.asyncio
async def test_build_draft_populates_ctx_ledger_beam(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    config = EngineConfig(
        config_version="test",
        assembly=AssemblyConfig(beam_width=1),
        flags=EngineFlags(use_beam_search=True),
    )
    program = _build(ctx, sample_template_orm, definition, sample_exercises, config=config)
    expected = compute_ledger(program, sample_exercises)
    actual = ctx.ledger.snapshot()
    for group in MUSCLE_GROUPS:
        assert actual[group].effective_sets_week == pytest.approx(expected[group].effective_sets_week)
        assert actual[group].frequency_days == expected[group].frequency_days


# --- Post-draft volume validator (plan §2.5, decision #6) -------------------------

_ZERO_WEIGHTS = SelectionWeights(
    variety=0.0,
    priority_fit=0.0,
    muscle_fit=0.0,
    difficulty=0.0,
    unilateral_balance=0.0,
    movement_preference=0.0,
    complementary_coverage=0.0,
)


def _validator_exercise(id_: int, slug: str, *, primary: list[str], secondary: list[str] | None = None) -> Exercise:
    return Exercise(
        id=id_,
        name=slug,
        slug=slug,
        movement_slug=slug,
        body_region=BodyRegion.FULL_BODY,
        movement_pattern=MovementPattern.HORIZONTAL_PUSH,
        primary_muscles=primary,
        secondary_muscles=secondary or [],
        equipment_tags=[],
        difficulty_level=ExperienceLevel.INTERMEDIATE,
        instructions="Do the thing.",
        form_cues=[],
        contraindications=[],
        is_active=True,
    )


def _filler_workout_exercises(start_id: int) -> tuple[list[Exercise], list[WorkoutExercise]]:
    """One locked, in-band (12 effective sets, intermediate band [8, 22]) WorkoutExercise
    per group other than "chest" -- so only "chest" is ever a volume violation in these
    tests, and the 14 filler rows (locked) are never eligible reselection targets."""
    exercises: list[Exercise] = []
    workout_exercises: list[WorkoutExercise] = []
    muscle_for_group = {
        "back": "lats",
        "traps": "traps",
        "shoulders": "shoulders_anterior",
        "biceps": "biceps",
        "triceps": "triceps",
        "forearms": "forearms",
        "quads": "quads",
        "hamstrings": "hamstrings",
        "glutes": "glutes",
        "calves": "calves",
        "abs": "abs",
        "obliques": "obliques",
        "lower_back": "lower_back",
        "hips": "hip_flexors",
    }
    assert set(muscle_for_group) == set(MUSCLE_GROUPS) - {"chest"}
    for i, (group, muscle) in enumerate(muscle_for_group.items()):
        ex_id = start_id + i
        ex = _validator_exercise(ex_id, f"filler-{group}", primary=[muscle])
        exercises.append(ex)
        workout_exercises.append(
            WorkoutExercise(
                id=ex_id,
                order=i,
                exercise_id=ex_id,
                fills_rule={},
                sets=12,
                reps_min=8,
                reps_max=12,
                base_load=None,
                rest_seconds=90,
                scheme_key="main",
                target_rpe=None,
                intensity_pct=None,
                is_locked=True,
                is_user_swapped=False,
                rotation_pool=[],
            )
        )
    return exercises, workout_exercises


def _ledger_test_ctx() -> SelectionContext:
    return SelectionContext(
        equipment=[],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
        weights=_ZERO_WEIGHTS,
    )


_CHEST_RULE = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory")


def _chest_program(chest_we_exercise_id: int, chest_sets: int) -> tuple[WorkoutProgram, list[Exercise]]:
    filler_exercises, filler_wes = _filler_workout_exercises(start_id=100)
    chest_we = WorkoutExercise(
        id=1,
        order=99,
        exercise_id=chest_we_exercise_id,
        fills_rule=_CHEST_RULE.model_dump(),
        sets=chest_sets,
        reps_min=8,
        reps_max=12,
        base_load=None,
        rest_seconds=90,
        scheme_key="accessory",
        target_rpe=None,
        intensity_pct=None,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=[],
    )
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=0)
    workout.exercises = [*filler_wes, chest_we]
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Validator Test Program",
        focus=None,
        status="draft",
        duration_weeks=8,
        days_per_week=1,
        weight_unit="kg",
        constraints={"excluded_exercise_ids": [], "swaps": {}},
    )
    program.workouts = [workout]
    return program, filler_exercises


def test_validate_and_repair_volume_resolves_when_a_better_candidate_exists():
    """ex_current (id=5) credits chest only as a SECONDARY muscle (0.5x); ex_better
    (id=1, lower id -- wins the all-zero-weight tie in select_for_slot) credits chest
    as PRIMARY (1.0x). Reselection swaps the slot to ex_better, pushing chest's
    effective sets from 5.0 (< MEV=8) to 10.0 (>= MEV) without changing `we.sets`."""
    ex_current = _validator_exercise(5, "current", primary=["cardio"], secondary=["chest"])
    ex_better = _validator_exercise(1, "better", primary=["chest"])
    program, filler_exercises = _chest_program(chest_we_exercise_id=5, chest_sets=10)
    exercises = [*filler_exercises, ex_current, ex_better]

    config = EngineConfig(config_version="x", flags=EngineFlags(use_volume_validator=True))
    ctx = _ledger_test_ctx()
    sink: list = []
    _validate_and_repair_volume(program, None, ctx, exercises, config, sink)

    ledger = compute_ledger(program, exercises)
    assert ledger["chest"].effective_sets_week >= 8.0
    assert program.workouts[0].exercises[-1].exercise_id == 1  # swapped to ex_better
    assert sink == []  # resolved -- no advisory


def test_validate_and_repair_volume_surfaces_advisory_when_unresolvable():
    """Both available candidates for the chest slot only credit chest as a SECONDARY
    muscle (0.5x): no matter which one `_reselect` picks, chest's effective sets can't
    cross MEV. Exactly one Advisory must be emitted for it."""
    ex_current = _validator_exercise(5, "current", primary=["cardio"], secondary=["chest"])
    ex_alt = _validator_exercise(2, "alt", primary=["cardio"], secondary=["chest"])
    program, filler_exercises = _chest_program(chest_we_exercise_id=5, chest_sets=10)
    exercises = [*filler_exercises, ex_current, ex_alt]

    config = EngineConfig(config_version="x", flags=EngineFlags(use_volume_validator=True))
    ctx = _ledger_test_ctx()
    sink: list = []
    _validate_and_repair_volume(program, None, ctx, exercises, config, sink)

    ledger = compute_ledger(program, exercises)
    assert ledger["chest"].effective_sets_week < 8.0
    assert len(sink) == 1
    assert sink[0].code == "VOLUME_BELOW_MEV"
    assert sink[0].subject == "chest"
    assert sink[0].severity == "warning"


def test_validate_and_repair_volume_advisory_sink_none_does_not_crash():
    ex_current = _validator_exercise(5, "current", primary=["cardio"], secondary=["chest"])
    ex_alt = _validator_exercise(2, "alt", primary=["cardio"], secondary=["chest"])
    program, filler_exercises = _chest_program(chest_we_exercise_id=5, chest_sets=10)
    exercises = [*filler_exercises, ex_current, ex_alt]

    config = EngineConfig(config_version="x", flags=EngineFlags(use_volume_validator=True))
    ctx = _ledger_test_ctx()
    _validate_and_repair_volume(program, None, ctx, exercises, config, None)  # must not raise


@pytest.mark.asyncio
async def test_build_draft_wires_advisories_through_when_validator_enabled(sample_template_orm, sample_exercises):
    """Integration check: build_draft's advisory_sink actually gets populated end-to-end
    when a real EngineConfig with `flags.use_volume_validator=True` is passed (the sample
    template's volumes are well below intermediate MEV for most groups, so this should
    fire). Uses the dedicated validator flag, not lambda_v/lambda_f -- those are
    assembly-objective scoring weights and must not also gate this separate, mutating
    mechanism (see AssemblyConfig's docstring)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    config = EngineConfig(config_version="test", flags=EngineFlags(use_volume_validator=True))
    sink: list = []
    build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        config=config,
        advisory_sink=sink,
    )
    assert sink  # at least one unresolved violation surfaced
    assert all(a.code in ("VOLUME_BELOW_MEV", "VOLUME_ABOVE_MRV") for a in sink)


@pytest.mark.asyncio
async def test_build_draft_lambda_nonzero_alone_does_not_enable_validator(sample_template_orm, sample_exercises):
    """Regression test for the reviewed gating bug: a nonzero lambda_v/lambda_f must
    NOT enable the post-draft volume validator on its own (greedy path, use_beam_search
    at its default False, use_volume_validator at its default False). lambda_v/lambda_f
    are assembly-objective scoring weights only; the validator requires its own,
    separate `flags.use_volume_validator=True`."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    config = EngineConfig(config_version="test", assembly=AssemblyConfig(lambda_v=1.0, lambda_f=1.0))
    sink: list = []
    build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
        config=config,
        advisory_sink=sink,
    )
    assert sink == []  # validator never ran -- no advisories, no mutation


def _volume_regression_build_draft_inputs() -> tuple[ProgramTemplate, TemplateDefinition, list[Exercise]]:
    """Hand-built two-workout template driving the real build_draft path, where every
    WorkoutExercise.id is None until the program is persisted -- unlike the
    _chest_program()-based unit tests above, which hand-construct rows with explicit
    `id=` values and so can't exercise the id=None lookup bug at all.

    Session "day_1" has a single "back" slot, deliberately kept in-band (10 effective
    sets, within intermediate [8, 22]) so it never violates. Session "day_2" has a
    single "chest" slot with enough sets (30) to push "chest" above the intermediate
    MRV guard (22) -- uniquely, since no other slot contributes to "chest" at all, so
    the validator's max-contribution search has exactly one correct answer: day_2's
    slot, not day_1's (which happens to be first in iteration order).
    """
    template = ProgramTemplate(id=1, name="Volume Regression Test", slug="volume-regression-test", goals=[])
    definition = TemplateDefinition(
        split=SplitDef(
            sessions=[
                SessionDef(
                    key="day_1",
                    name="Day 1",
                    order=1,
                    slots=[SlotRule(pattern="vertical_pull", priority="accessory", scheme="back")],
                ),
                SessionDef(
                    key="day_2",
                    name="Day 2",
                    order=2,
                    slots=[SlotRule(pattern="horizontal_push", priority="accessory", scheme="chest")],
                ),
            ]
        ),
        progression=ProgressionRef(model_key="linear_load"),
        schemes={
            "back": SchemeDef(sets=10, reps_min=8, reps_max=12, rest_seconds=90),
            "chest": SchemeDef(sets=30, reps_min=8, reps_max=12, rest_seconds=90),
        },
    )
    back_ex = _validator_exercise(1, "back-row", primary=["lats"])
    back_ex.movement_pattern = MovementPattern.VERTICAL_PULL
    # Two chest candidates with distinct movement_slugs: the initial greedy fill picks
    # chest_current (lower id wins an all-else-tied ranking); once it's placed, its
    # movement_slug is marked "used" in ctx, so a correct reselect -- scoring the same
    # slot's rule against the same ctx -- naturally prefers chest_alt for variety. This
    # makes "did the right slot get repaired" directly observable via exercise_id.
    chest_current = _validator_exercise(10, "chest-current", primary=["chest"])
    chest_alt = _validator_exercise(11, "chest-alt", primary=["chest"])
    return template, definition, [back_ex, chest_current, chest_alt]


@pytest.mark.asyncio
async def test_build_draft_volume_validator_repairs_the_correct_slot_not_the_first_slot():
    """Regression for the id=None `_reselect` bug (see adaptation.py's `_find_slot` /
    `_reselect_exercise`): on the real build_draft path, every WorkoutExercise.id is
    None pre-persist, so an id-based lookup of the validator's chosen target collapses
    to "the first id=None slot anywhere in program.workouts" -- always day_1's back
    slot here -- regardless of which slot the min/max-contribution search actually
    identified. The correct target is day_2's chest slot (the sole contributor pushing
    "chest" above the MRV guard). This test fails against the pre-fix code (verified by
    temporarily reverting the fix): day_1's slot never changes id (single candidate) so
    it wouldn't betray the bug either way, but day_2's chest slot would stay at
    chest-current (id=10) instead of being repaired to chest-alt (id=11)."""
    template, definition, exercises = _volume_regression_build_draft_inputs()
    ctx = SelectionContext(equipment=[], experience="intermediate", injuries=[], used_movement_slugs=set())
    config = EngineConfig(config_version="x", flags=EngineFlags(use_volume_validator=True))
    sink: list = []
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=1,
        environment_id=1,
        days_per_week=2,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={},
        config=config,
        advisory_sink=sink,
    )

    back_workout = next(w for w in program.workouts if w.key == "day_1")
    chest_workout = next(w for w in program.workouts if w.key == "day_2")

    assert back_workout.exercises[0].exercise_id == 1  # untouched: not the violated slot
    assert chest_workout.exercises[0].exercise_id == 11  # repaired: chest-current -> chest-alt


# --- Interference scheduler (Task 2.7b) -------------------------------------------------


def _interference_workout_exercise(
    id_: int, order: int, exercise_id: int, *, pattern: str, priority: str
) -> WorkoutExercise:
    return WorkoutExercise(
        id=id_,
        order=order,
        exercise_id=exercise_id,
        fills_rule={"pattern": pattern, "priority": priority},
        sets=3,
        reps_min=5,
        reps_max=8,
        base_load=None,
        rest_seconds=120,
        scheme_key="main",
        target_rpe=None,
        intensity_pct=None,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=[],
    )


def _interference_program(workout: Workout) -> WorkoutProgram:
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Interference Test Program",
        focus=None,
        status="draft",
        duration_weeks=8,
        days_per_week=1,
        weight_unit="kg",
        constraints={"excluded_exercise_ids": [], "swaps": {}},
    )
    program.workouts = [workout]
    return program


def test_apply_interference_scheduling_advisory_fires_even_when_already_ordered():
    """Strength already precedes conditioning in the original order: no reordering is
    needed, but the advisory must still fire -- the ≥6h-separation recommendation is
    about real-world scheduling, not display order (decision 4)."""
    strength_ex = _validator_exercise(1, "back-squat", primary=["quads"])
    cardio_ex = _validator_exercise(2, "jogging", primary=["cardio"])
    we_strength = _interference_workout_exercise(1, 1, 1, pattern="squat", priority="primary")
    we_cardio = _interference_workout_exercise(2, 2, 2, pattern="locomotion", priority="accessory")
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we_strength, we_cardio]
    program = _interference_program(workout)

    sink: list = []
    _apply_interference_scheduling(program, [strength_ex, cardio_ex], sink)

    assert [we.id for we in workout.exercises] == [1, 2]  # unchanged
    assert [we.order for we in workout.exercises] == [1, 2]  # unchanged
    assert len(sink) == 1
    assert sink[0].code == "CONDITIONING_SEPARATION_RECOMMENDED"
    assert sink[0].severity == "info"
    assert sink[0].subject == "day_1"


def test_apply_interference_scheduling_reorders_when_conditioning_precedes_strength():
    """Conditioning originally precedes strength: the pass must actually reorder so the
    conditioning slot's `.order` ends up greater than the strength slot's, and the
    in-memory list itself (not just `.order`) must reflect the new sequence."""
    strength_ex = _validator_exercise(1, "back-squat", primary=["quads"])
    cardio_ex = _validator_exercise(2, "jogging", primary=["cardio"])
    we_cardio = _interference_workout_exercise(1, 1, 2, pattern="locomotion", priority="accessory")
    we_strength = _interference_workout_exercise(2, 2, 1, pattern="squat", priority="primary")
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we_cardio, we_strength]
    program = _interference_program(workout)

    sink: list = []
    _apply_interference_scheduling(program, [strength_ex, cardio_ex], sink)

    assert [we.id for we in workout.exercises] == [2, 1]  # strength row now iterates first
    assert we_strength.order < we_cardio.order
    assert [we.order for we in workout.exercises] == [1, 2]
    assert len(sink) == 1


def test_apply_interference_scheduling_stable_sort_preserves_relative_order_within_groups():
    """Multiple strength and multiple conditioning slots, interleaved: after the pass,
    every strength slot precedes every conditioning slot, and each group's *relative*
    order from the original sequence is preserved (proves stability, not just
    "some" reordering) -- verified against the actual list iteration order."""
    strength_ex = _validator_exercise(1, "back-squat", primary=["quads"])
    cardio_ex = _validator_exercise(2, "jogging", primary=["cardio"])
    we_s1 = _interference_workout_exercise(10, 1, 1, pattern="squat", priority="primary")
    we_c1 = _interference_workout_exercise(20, 2, 2, pattern="locomotion", priority="accessory")
    we_s2 = _interference_workout_exercise(11, 3, 1, pattern="hinge", priority="primary")
    we_c2 = _interference_workout_exercise(21, 4, 2, pattern="locomotion", priority="accessory")
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we_s1, we_c1, we_s2, we_c2]
    program = _interference_program(workout)

    sink: list = []
    _apply_interference_scheduling(program, [strength_ex, cardio_ex], sink)

    # Strength group (we_s1, we_s2) keeps its relative order, then conditioning group
    # (we_c1, we_c2) keeps its relative order -- this is what `.id` order proves that
    # checking only the renumbered `.order` integers would not.
    assert [we.id for we in workout.exercises] == [10, 11, 20, 21]
    assert [we.order for we in workout.exercises] == [1, 2, 3, 4]
    assert len(sink) == 1


def test_apply_interference_scheduling_no_op_without_strength():
    """Conditioning slot present, but the only lower-body slot is accessory priority
    (not primary) -- doesn't count as "heavy lower-body strength": no reorder, no
    advisory."""
    accessory_ex = _validator_exercise(1, "goblet-squat", primary=["quads"])
    cardio_ex = _validator_exercise(2, "jogging", primary=["cardio"])
    we_accessory = _interference_workout_exercise(1, 1, 1, pattern="squat", priority="accessory")
    we_cardio = _interference_workout_exercise(2, 2, 2, pattern="locomotion", priority="accessory")
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we_accessory, we_cardio]
    program = _interference_program(workout)

    sink: list = []
    _apply_interference_scheduling(program, [accessory_ex, cardio_ex], sink)

    assert [we.id for we in workout.exercises] == [1, 2]
    assert sink == []


def test_apply_interference_scheduling_no_op_without_conditioning():
    """Heavy lower-body strength slot present, but no conditioning slot: no reorder, no
    advisory."""
    strength_ex = _validator_exercise(1, "back-squat", primary=["quads"])
    upper_ex = _validator_exercise(2, "bench-press", primary=["chest"])
    we_strength = _interference_workout_exercise(1, 1, 1, pattern="squat", priority="primary")
    we_upper = _interference_workout_exercise(2, 2, 2, pattern="horizontal_push", priority="primary")
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we_strength, we_upper]
    program = _interference_program(workout)

    sink: list = []
    _apply_interference_scheduling(program, [strength_ex, upper_ex], sink)

    assert [we.id for we in workout.exercises] == [1, 2]
    assert sink == []


def _interference_build_draft_inputs() -> tuple[ProgramTemplate, TemplateDefinition, list[Exercise]]:
    """Hand-built template/definition placing a conditioning slot before a heavy
    lower-body-strength slot in one session -- exercises this codebase's real seed
    catalog can't (zero seeded templates define any locomotion-pattern slot, per the
    brief), so build_draft's call-site gating can be exercised end to end."""
    template = ProgramTemplate(id=1, name="Interference Gate Test", slug="interference-gate-test", goals=[])
    definition = TemplateDefinition(
        split=SplitDef(
            sessions=[
                SessionDef(
                    key="day_1",
                    name="Day 1",
                    order=1,
                    slots=[
                        SlotRule(pattern="locomotion", priority="accessory", scheme="cardio"),
                        SlotRule(pattern="squat", priority="primary", scheme="main"),
                    ],
                )
            ]
        ),
        progression=ProgressionRef(model_key="linear_load"),
        schemes={
            "cardio": SchemeDef(sets=1, reps_min=1, reps_max=1, rest_seconds=60),
            "main": SchemeDef(sets=3, reps_min=5, reps_max=5, rest_seconds=120),
        },
    )
    squat_ex = _validator_exercise(1, "back-squat", primary=["quads"], secondary=["glutes"])
    squat_ex.movement_pattern = MovementPattern.SQUAT
    squat_ex.body_region = BodyRegion.LOWER_BODY
    cardio_ex = _validator_exercise(2, "jogging", primary=["cardio"])
    cardio_ex.movement_pattern = MovementPattern.LOCOMOTION
    return template, definition, [cardio_ex, squat_ex]


def _build_interference_draft(config: EngineConfig | None) -> tuple[WorkoutProgram, list]:
    template, definition, exercises = _interference_build_draft_inputs()
    ctx = SelectionContext(equipment=[], experience="intermediate", injuries=[], used_movement_slugs=set())
    sink: list = []
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=1,
        environment_id=1,
        days_per_week=1,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={},
        config=config,
        advisory_sink=sink,
    )
    return program, sink


def test_build_draft_config_none_never_triggers_interference_scheduling():
    """config=None (today's production default): the pass must not run -- no reorder,
    no advisories -- proving the feature is fully inert without the flag."""
    program, sink = _build_interference_draft(config=None)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [2, 1]  # original slot order: cardio, then squat
    assert sink == []


def test_build_draft_flag_explicitly_off_never_triggers_interference_scheduling():
    """config supplied but flags.use_interference_scheduler=False (explicit default)
    also stays inert -- mirrors the exact gate-correctness regression test pattern used
    for every prior Phase 2 flag addition."""
    config = EngineConfig(config_version="x", flags=EngineFlags(use_interference_scheduler=False))
    program, sink = _build_interference_draft(config)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [2, 1]
    assert sink == []


def test_build_draft_wires_interference_advisory_through_when_enabled():
    """End-to-end: with the flag on, build_draft's own call site actually invokes the
    pass and its advisory_sink gets populated."""
    config = EngineConfig(config_version="x", flags=EngineFlags(use_interference_scheduler=True))
    program, sink = _build_interference_draft(config)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [1, 2]  # squat now precedes cardio
    assert len(sink) == 1
    assert sink[0].code == "CONDITIONING_SEPARATION_RECOMMENDED"


# --- Safety substitution (Task 3.3) -----------------------------------------------------


def _safety_exercise(
    id_: int,
    slug: str,
    *,
    movement_pattern: MovementPattern,
    equipment_tags: list[str] | None = None,
    provocation_tags: list[str] | None = None,
) -> Exercise:
    return Exercise(
        id=id_,
        name=slug,
        slug=slug,
        movement_slug=slug,
        body_region=BodyRegion.FULL_BODY,
        movement_pattern=movement_pattern,
        primary_muscles=["quads"],
        secondary_muscles=[],
        equipment_tags=equipment_tags or [],
        difficulty_level=ExperienceLevel.INTERMEDIATE,
        instructions="Do the thing.",
        form_cues=[],
        contraindications=[],
        provocation_tags=provocation_tags or [],
        is_active=True,
    )


def _safety_workout_exercise(id_: int, exercise_id: int, *, base_load: float | None = None) -> WorkoutExercise:
    return WorkoutExercise(
        id=id_,
        order=1,
        exercise_id=exercise_id,
        fills_rule={"pattern": "squat", "priority": "primary"},
        sets=3,
        reps_min=5,
        reps_max=8,
        base_load=base_load,
        rest_seconds=120,
        scheme_key="main",
        target_rpe=None,
        intensity_pct=None,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=[],
    )


def _safety_ctx(*, equipment: list[str], provocations: list[ActiveInjuryProvocation]) -> SelectionContext:
    return SelectionContext(
        equipment=equipment,
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
        injury_provocations=provocations,
    )


def _safety_graphs(edges: list[RegressionEdge]) -> RegressionGraphsConfig:
    return RegressionGraphsConfig(config_version="test", rehabilitating_load_multiplier=0.8, patterns={"squat": edges})


def test_apply_safety_substitution_picks_nearest_regression_over_cross_pattern():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    regression_ex = _safety_exercise(
        2, "reg-squat", movement_pattern=MovementPattern.SQUAT, equipment_tags=["dumbbells"]
    )
    cross_ex = _safety_exercise(3, "cross-hinge", movement_pattern=MovementPattern.HINGE, equipment_tags=["none"])
    graphs = _safety_graphs(
        [
            RegressionEdge(from_slug="main-squat", to="reg-squat", kind="regression", relieves=["axial_loading"]),
            RegressionEdge(from_slug="main-squat", to="cross-hinge", kind="cross_pattern", relieves=["axial_loading"]),
        ]
    )
    ctx = _safety_ctx(
        equipment=["barbell", "dumbbells", "none"],
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=False)],
    )
    we = _safety_workout_exercise(1, 1, base_load=100.0)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex, regression_ex, cross_ex], ctx, graphs, sink)

    assert we.exercise_id == 2  # regression preferred over cross-pattern
    assert we.base_load == 100.0  # not rehabilitating -> no load cap
    assert len(sink) == 1
    assert sink[0].code == "SAFETY_SUBSTITUTION"
    assert sink[0].severity == "info"
    assert sink[0].subject == "day_1"


def test_apply_safety_substitution_falls_back_to_cross_pattern_when_regression_not_in_equipment():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    regression_ex = _safety_exercise(
        2, "reg-squat", movement_pattern=MovementPattern.SQUAT, equipment_tags=["squat_rack"]
    )
    cross_ex = _safety_exercise(3, "cross-hinge", movement_pattern=MovementPattern.HINGE, equipment_tags=["none"])
    graphs = _safety_graphs(
        [
            RegressionEdge(from_slug="main-squat", to="reg-squat", kind="regression", relieves=["axial_loading"]),
            RegressionEdge(from_slug="main-squat", to="cross-hinge", kind="cross_pattern", relieves=["axial_loading"]),
        ]
    )
    ctx = _safety_ctx(
        equipment=["barbell", "none"],  # squat_rack unavailable -> regression not permissible
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=False)],
    )
    we = _safety_workout_exercise(1, 1)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex, regression_ex, cross_ex], ctx, graphs, sink)

    assert we.exercise_id == 3
    assert sink[0].code == "SAFETY_SUBSTITUTION"


def test_apply_safety_substitution_removes_slot_when_no_substitute_is_permissible():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    graphs = _safety_graphs([])  # no edges at all for this pattern
    ctx = _safety_ctx(
        equipment=["barbell"],
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=False)],
    )
    we = _safety_workout_exercise(1, 1)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex], ctx, graphs, sink)

    assert workout.exercises == []
    assert len(sink) == 1
    assert sink[0].code == "SAFETY_EXCLUSION"
    assert sink[0].severity == "warning"


def test_apply_safety_substitution_applies_rehab_load_multiplier_on_substitution():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    regression_ex = _safety_exercise(
        2, "reg-squat", movement_pattern=MovementPattern.SQUAT, equipment_tags=["dumbbells"]
    )
    graphs = _safety_graphs(
        [RegressionEdge(from_slug="main-squat", to="reg-squat", kind="regression", relieves=["axial_loading"])]
    )
    ctx = _safety_ctx(
        equipment=["barbell", "dumbbells"],
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=True)],
    )
    we = _safety_workout_exercise(1, 1, base_load=100.0)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex, regression_ex], ctx, graphs, sink)

    assert we.exercise_id == 2
    assert we.base_load == 80.0  # 100 * rehabilitating_load_multiplier (0.8)


def test_apply_safety_substitution_no_op_without_injury_provocations():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    graphs = _safety_graphs([])
    ctx = _safety_ctx(equipment=["barbell"], provocations=[])
    we = _safety_workout_exercise(1, 1)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex], ctx, graphs, sink)

    assert we.exercise_id == 1
    assert sink == []


def test_apply_safety_substitution_no_op_when_exercise_not_hit():
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["deep_knee_flexion"],
    )
    graphs = _safety_graphs([])
    ctx = _safety_ctx(
        equipment=["barbell"],
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=False)],
    )
    we = _safety_workout_exercise(1, 1)
    workout = Workout(id=1, key="day_1", name="Day 1", focus=None, order=1)
    workout.exercises = [we]
    program = _interference_program(workout)

    sink: list = []
    _apply_safety_substitution(program, [main_ex], ctx, graphs, sink)

    assert we.exercise_id == 1
    assert sink == []


def _safety_build_draft_inputs() -> tuple[ProgramTemplate, TemplateDefinition, list[Exercise]]:
    template = ProgramTemplate(id=1, name="Safety Gate Test", slug="safety-gate-test", goals=[])
    definition = TemplateDefinition(
        split=SplitDef(
            sessions=[
                SessionDef(
                    key="day_1",
                    name="Day 1",
                    order=1,
                    slots=[SlotRule(pattern="squat", priority="primary", scheme="main")],
                )
            ]
        ),
        progression=ProgressionRef(model_key="linear_load"),
        schemes={"main": SchemeDef(sets=3, reps_min=5, reps_max=5, rest_seconds=120)},
    )
    main_ex = _safety_exercise(
        1,
        "main-squat",
        movement_pattern=MovementPattern.SQUAT,
        equipment_tags=["barbell"],
        provocation_tags=["axial_loading"],
    )
    regression_ex = _safety_exercise(2, "reg-squat", movement_pattern=MovementPattern.SQUAT, equipment_tags=["barbell"])
    return template, definition, [main_ex, regression_ex]


def _build_safety_draft(config: EngineConfig | None) -> tuple[WorkoutProgram, list]:
    template, definition, exercises = _safety_build_draft_inputs()
    graphs = _safety_graphs(
        [RegressionEdge(from_slug="main-squat", to="reg-squat", kind="regression", relieves=["axial_loading"])]
    )
    ctx = _safety_ctx(
        equipment=["barbell"],
        provocations=[ActiveInjuryProvocation(provocation="axial_loading", is_rehabilitating=False)],
    )
    sink: list = []
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=1,
        environment_id=1,
        days_per_week=1,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={},
        config=config,
        advisory_sink=sink,
        regression_graphs=graphs,
    )
    return program, sink


def test_build_draft_config_none_never_triggers_safety_substitution():
    """config=None (today's production default): the pass must not run."""
    program, sink = _build_safety_draft(config=None)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [1]  # untouched main-squat pick
    assert sink == []


def test_build_draft_flag_explicitly_off_never_triggers_safety_substitution():
    config = EngineConfig(config_version="x", flags=EngineFlags(use_safety_substitution=False))
    program, sink = _build_safety_draft(config)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [1]
    assert sink == []


def test_build_draft_wires_safety_substitution_advisory_through_when_enabled():
    """End-to-end: with the flag on, build_draft's own call site actually invokes the
    pass and substitutes the contraindicated pick."""
    config = EngineConfig(config_version="x", flags=EngineFlags(use_safety_substitution=True))
    program, sink = _build_safety_draft(config)
    workout = program.workouts[0]
    assert [we.exercise_id for we in workout.exercises] == [2]  # reg-squat substituted in
    assert len(sink) == 1
    assert sink[0].code == "SAFETY_SUBSTITUTION"
