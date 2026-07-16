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
