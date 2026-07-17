import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext


@pytest.mark.asyncio
async def test_derive_week_applies_progression(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:  # give ids so derive output is stable
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    w1 = derive_week(program, definition, 1, exercise_map)
    w2 = derive_week(program, definition, 2, exercise_map)
    load1 = next((s["load"] for d in w1 for s in d["slots"] if s["load"] is not None), None)
    load2 = next((s["load"] for d in w2 for s in d["slots"] if s["load"] is not None), None)
    assert load2 > load1  # progression increased load week over week


@pytest.mark.asyncio
async def test_derive_week_horizontal_push_load_is_seeded(sample_template_orm, sample_exercises):
    """Regression: horizontal_push slot's load must be seeded from bench_start via applies_to."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id

    horizontal_push_we_ids = {
        ex.id for w in program.workouts for ex in w.exercises if ex.fills_rule.get("pattern") == "horizontal_push"
    }
    assert horizontal_push_we_ids

    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    loads = [s["load"] for d in week1 for s in d["slots"] if s["workout_exercise_id"] in horizontal_push_we_ids]
    assert loads
    assert all(load is not None for load in loads)
    # Verify exercise names are resolved from the exercise map
    exercise_names = [
        s["exercise_name"] for d in week1 for s in d["slots"] if s["workout_exercise_id"] in horizontal_push_we_ids
    ]
    assert exercise_names
    assert all(not name.startswith("Exercise #") for name in exercise_names)


@pytest.mark.asyncio
async def test_derive_week_includes_exercise_names(sample_template_orm, sample_exercises):
    """Verify exercise names are included in derived weeks."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    for slot in slots:
        assert "exercise_name" in slot
        assert slot["exercise_name"]  # not empty
        # Should have real name from exercise_map, not fallback
        assert not slot["exercise_name"].startswith("Exercise #")


@pytest.mark.asyncio
async def test_derive_week_includes_rpe_effort_target_when_requested(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
        effort_method="rpe",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    main_slots = [s for d in week1 for s in d["slots"] if s.get("effort_target") is not None]
    assert main_slots
    assert all(s["effort_target"]["method"] == "rpe" for s in main_slots)


@pytest.mark.asyncio
async def test_derive_week_converts_rpe_to_rir(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
        effort_method="rir",
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # Only main-scheme slots have target_rpe=8.0; the template also fills some accessory-scheme
    # slots (target_rpe=7.0), so scope the assertion to workout_exercises using the main scheme.
    main_we_ids = {ex.id for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"}
    main_targets = [
        s["effort_target"]
        for d in week1
        for s in d["slots"]
        if s["workout_exercise_id"] in main_we_ids and s.get("effort_target") is not None
    ]
    assert main_targets
    assert all(t["method"] == "rir" for t in main_targets)
    assert all(t["value"] == 2 for t in main_targets)  # target_rpe=8.0 -> rir = 10 - 8 = 2


@pytest.mark.asyncio
async def test_derive_week_percent_1rm_target_includes_load(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 100, "bench_start": 80},
        effort_method="percent_1rm",
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # target_load is only seeded for patterns with an applies_to required input (squat,
    # horizontal_push); other patterns have no starting weight and load stays None.
    seeded_we_ids = {
        ex.id
        for w in program.workouts
        for ex in w.exercises
        if ex.fills_rule.get("pattern") in ("squat", "horizontal_push")
    }
    targets = [
        s["effort_target"]
        for d in week1
        for s in d["slots"]
        if s["workout_exercise_id"] in seeded_we_ids and s.get("effort_target") is not None
    ]
    assert targets
    assert all(t["method"] == "percent_1rm" for t in targets)
    assert all(t["pct"] in (0.8, 0.65) for t in targets)  # main=0.8, accessory=0.65 intensity_pct
    assert all(t["target_load"] is not None for t in targets)


@pytest.mark.asyncio
async def test_derive_week_omits_effort_target_when_effort_method_unset(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    assert all(s["effort_target"] is None for s in slots)  # backward compatible default


@pytest.mark.asyncio
async def test_derive_week_applies_rotation_pool_week_to_week(sample_template_orm, sample_exercises):
    """Rotation pool cycles the resolved exercise week over week and is surfaced in the slot."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}

    target_we = program.workouts[0].exercises[0]
    pool = [e.id for e in sample_exercises[:3]]
    target_we.rotation_pool = pool

    def slot_for(week: int) -> dict:
        days = derive_week(program, definition, week, exercise_map)
        return next(s for d in days for s in d["slots"] if s["workout_exercise_id"] == target_we.id)

    week1_slot = slot_for(1)
    assert week1_slot["exercise_id"] == pool[0]
    assert week1_slot["rotation_pool"] == pool

    week4_slot = slot_for(len(pool) + 1)  # cycles back to pool[0]
    assert week4_slot["exercise_id"] == pool[0]

    week2_slot = slot_for(2)
    assert week2_slot["exercise_id"] == pool[1]


@pytest.mark.asyncio
async def test_derive_week_fallback_for_missing_exercise(sample_template_orm, sample_exercises):
    """Verify placeholder name when exercise is missing (e.g., deactivated)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
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
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    # Empty exercise map simulates all exercises being deactivated
    week1 = derive_week(program, definition, 1, {})
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    for slot in slots:
        # Should all be fallback placeholders
        assert slot["exercise_name"].startswith("Exercise #")
