import pytest

from app.core.exceptions import ValidationError
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


def _find_by_pattern(program, pattern: str):
    for w in program.workouts:
        for ex in w.exercises:
            if ex.fills_rule.get("pattern") == pattern:
                return ex
    return None


@pytest.mark.asyncio
async def test_swap_to_valid_alternative_succeeds(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = _find_by_pattern(program, "horizontal_push")
    assert target is not None

    valid_alternative = next(
        e for e in sample_exercises if e.movement_pattern.value == "horizontal_push" and e.id != target.exercise_id
    )

    apply_feedback(
        program,
        definition,
        FeedbackAction(type="swap", workout_exercise_id=target.id, exercise_id=valid_alternative.id),
        ctx,
        sample_exercises,
    )
    assert target.exercise_id == valid_alternative.id
    assert target.is_user_swapped is True
    assert program.constraints["swaps"][str(target.id)] == valid_alternative.id


@pytest.mark.asyncio
async def test_swap_to_wrong_pattern_raises_validation_error(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = _find_by_pattern(program, "horizontal_push")
    assert target is not None
    original_exercise_id = target.exercise_id

    wrong_pattern_exercise = next(e for e in sample_exercises if e.movement_pattern.value == "squat")

    with pytest.raises(ValidationError):
        apply_feedback(
            program,
            definition,
            FeedbackAction(type="swap", workout_exercise_id=target.id, exercise_id=wrong_pattern_exercise.id),
            ctx,
            sample_exercises,
        )
    assert target.exercise_id == original_exercise_id
    assert target.is_user_swapped is False


@pytest.mark.asyncio
async def test_swap_to_nonexistent_exercise_raises_validation_error(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = _find_by_pattern(program, "horizontal_push")
    assert target is not None
    original_exercise_id = target.exercise_id

    with pytest.raises(ValidationError):
        apply_feedback(
            program,
            definition,
            FeedbackAction(type="swap", workout_exercise_id=target.id, exercise_id=999999),
            ctx,
            sample_exercises,
        )
    assert target.exercise_id == original_exercise_id
    assert target.is_user_swapped is False
