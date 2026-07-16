import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.adaptation import FeedbackAction, apply_feedback
from app.services.program.drafting import build_draft
from app.services.program.selection import SelectionContext


def _program(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack", "dumbbells"], "intermediate", [], set())
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
        required_inputs={},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = w.order * 100 + j
    return definition, ctx, program


@pytest.mark.asyncio
async def test_lock_then_regenerate_preserves_locked(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = program.workouts[0].exercises[0]
    locked_exercise = target.exercise_id
    apply_feedback(
        program, definition, FeedbackAction(type="lock", workout_exercise_id=target.id), ctx, sample_exercises
    )
    apply_feedback(
        program, definition, FeedbackAction(type="regenerate", workout_exercise_id=target.id), ctx, sample_exercises
    )
    assert program.workouts[0].exercises[0].exercise_id == locked_exercise
    assert target.id in program.constraints["locked_slots"]


@pytest.mark.asyncio
async def test_exclude_changes_exercise(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = program.workouts[0].exercises[0]
    original = target.exercise_id
    apply_feedback(
        program, definition, FeedbackAction(type="exclude", workout_exercise_id=target.id), ctx, sample_exercises
    )
    assert original in program.constraints["excluded_exercise_ids"]
