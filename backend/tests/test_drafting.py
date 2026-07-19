import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.engine_config import AssemblyConfig, EngineConfig, EngineFlags
from app.services.program.selection import SelectionContext


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
