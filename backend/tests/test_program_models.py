import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.models.program import ProgramStatus


@pytest.mark.asyncio
async def test_template_and_program_persist(db_session: AsyncSession, test_user):
    template = ProgramTemplate(
        name="Upper/Lower x4",
        slug="upper-lower-x4",
        description="",
        goals=["strength", "muscle_gain"],
        experience_levels=["intermediate"],
        days_per_week_min=4,
        days_per_week_max=4,
        session_duration_min=45,
        session_duration_max=75,
        split={"sessions": []},
        progression_ref={"model_key": "linear_load", "params": {}},
        required_inputs=[],
    )
    db_session.add(template)
    await db_session.flush()

    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=template.id,
        environment_id=1,
        name="My Program",
        focus="strength",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=4,
        weight_unit="kg",
        constraints={"locked_slots": [], "swaps": {}},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="upper_a", name="Upper A", focus="push,pull", order=1)
    db_session.add(workout)
    await db_session.flush()

    slot = WorkoutExercise(
        workout_id=workout.id,
        order=1,
        exercise_id=1,
        fills_rule={"pattern": "horizontal_push"},
        sets=3,
        reps_min=5,
        reps_max=5,
        base_load=60.0,
        rest_seconds=120,
        scheme_key="main",
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(slot)
    await db_session.commit()

    found = (await db_session.execute(select(WorkoutProgram))).scalar_one()
    assert found.status == ProgramStatus.DRAFT
    assert found.constraints["swaps"] == {}


@pytest.mark.asyncio
async def test_workout_exercise_rotation_pool_defaults_to_empty_list(db_session: AsyncSession, test_user):
    template = ProgramTemplate(
        name="Rotation Test",
        slug="rotation-test",
        description="",
        goals=["strength"],
        experience_levels=["intermediate"],
        days_per_week_min=3,
        days_per_week_max=3,
        session_duration_min=45,
        session_duration_max=75,
        split={"sessions": []},
        progression_ref={"model_key": "linear_load", "params": {}},
        required_inputs=[],
    )
    db_session.add(template)
    await db_session.flush()

    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=template.id,
        environment_id=1,
        name="P",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="a", name="A", order=1)
    db_session.add(workout)
    await db_session.flush()

    slot = WorkoutExercise(
        workout_id=workout.id,
        order=1,
        exercise_id=1,
        fills_rule={"pattern": "squat"},
        sets=3,
        reps_min=5,
        reps_max=5,
        rest_seconds=120,
        scheme_key="main",
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    assert slot.rotation_pool == []
