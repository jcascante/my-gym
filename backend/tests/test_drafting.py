import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.selection import SelectionContext


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
