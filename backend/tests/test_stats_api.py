from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramStatus, User, Workout, WorkoutProgram, WorkoutSession, WorkoutSetLog
from app.services.program.scheduling import materialize_sessions


@pytest_asyncio.fixture
async def active_program(db_session: AsyncSession, test_user: User, seeded_templates: None) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=1,
        environment_id=1,
        name="Test Program",
        status=ProgramStatus.ACTIVE,
        duration_weeks=4,
        days_per_week=3,
        start_date=date.today(),
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()
    for order, key in enumerate(["a", "b", "c"]):
        db_session.add(Workout(program_id=program.id, key=key, name=f"Day {key.upper()}", order=order))
    await db_session.commit()
    await db_session.refresh(program, ["workouts"])
    await materialize_sessions(db_session, program)
    return program


@pytest.mark.asyncio
async def test_stats_are_zeroed_with_no_active_program(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/users/me/stats")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "workouts_this_month": 0,
        "current_streak_days": 0,
        "personal_records": 0,
        "total_volume": 0.0,
        "weight_unit": "kg",
    }


@pytest.mark.asyncio
async def test_stats_reflect_a_completed_session_with_logged_sets(
    authenticated_client: AsyncClient,
    active_program: WorkoutProgram,
    db_session: AsyncSession,
) -> None:
    today_session_id = (
        await db_session.execute(
            select(WorkoutSession.id).where(
                WorkoutSession.program_id == active_program.id,
                WorkoutSession.scheduled_date == date.today(),
            )
        )
    ).scalar_one()

    db_session.add(
        WorkoutSetLog(
            user_id=1,
            workout_id=1,
            workout_exercise_id=1,
            session_id=today_session_id,
            set_number=1,
            actual_weight=100.0,
            actual_reps=5,
        )
    )
    await db_session.commit()

    await authenticated_client.post(f"/api/v1/users/me/sessions/{today_session_id}/complete")

    response = await authenticated_client.get("/api/v1/users/me/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["workouts_this_month"] == 1
    assert body["current_streak_days"] == 1
    assert body["personal_records"] == 1
    assert body["total_volume"] == 500.0
    assert body["weight_unit"] == "kg"


@pytest.mark.asyncio
async def test_stats_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me/stats")

    assert response.status_code == 401
