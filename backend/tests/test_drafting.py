import pytest

from app.models.exercise import BodyRegion, Exercise, ExperienceLevel, MovementPattern
from app.models.program import Workout, WorkoutExercise, WorkoutProgram
from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.drafting import _validate_and_repair_volume, build_draft
from app.services.program.engine_config import AssemblyConfig, EngineConfig, EngineFlags
from app.services.program.ledger import compute_ledger
from app.services.program.selection import SelectionContext, SelectionWeights
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

    config = EngineConfig(config_version="x", assembly=AssemblyConfig(lambda_v=1.0))
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

    config = EngineConfig(config_version="x", assembly=AssemblyConfig(lambda_v=1.0))
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

    config = EngineConfig(config_version="x", assembly=AssemblyConfig(lambda_v=1.0))
    ctx = _ledger_test_ctx()
    _validate_and_repair_volume(program, None, ctx, exercises, config, None)  # must not raise


@pytest.mark.asyncio
async def test_build_draft_wires_advisories_through_when_lambda_nonzero(sample_template_orm, sample_exercises):
    """Integration check: build_draft's advisory_sink actually gets populated end-to-end
    when a real EngineConfig with a nonzero lambda is passed (the sample template's
    volumes are well below intermediate MEV for most groups, so this should fire)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = _ctx()
    config = EngineConfig(config_version="test", assembly=AssemblyConfig(lambda_v=1.0))
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
