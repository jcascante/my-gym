from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, WorkoutSession


@pytest.mark.asyncio
async def test_session_defaults_to_scheduled(db_session: AsyncSession) -> None:
    session = WorkoutSession(program_id=1, workout_id=1, week=1, scheduled_date=date(2026, 7, 27))
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.status == SessionStatus.SCHEDULED
    assert session.completed_at is None


@pytest.mark.asyncio
async def test_program_workout_week_is_unique(db_session: AsyncSession) -> None:
    for _ in range(2):
        db_session.add(WorkoutSession(program_id=1, workout_id=1, week=1, scheduled_date=date(2026, 7, 27)))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_set_log_carries_a_session_id(db_session: AsyncSession) -> None:
    from app.models import WorkoutSetLog

    log = WorkoutSetLog(user_id=1, workout_id=1, workout_exercise_id=1, set_number=1, session_id=7)
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.session_id == 7


@pytest.mark.asyncio
async def test_set_log_without_a_session_is_rejected(db_session: AsyncSession) -> None:
    from app.models import WorkoutSetLog

    db_session.add(WorkoutSetLog(user_id=1, workout_id=1, workout_exercise_id=1, set_number=1))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_readiness_log_without_a_session_is_rejected(db_session: AsyncSession) -> None:
    from datetime import datetime

    from app.models import UserWorkoutLog

    db_session.add(UserWorkoutLog(user_id=1, workout_id=1, session_date=datetime(2026, 7, 27), readiness=4))

    with pytest.raises(IntegrityError):
        await db_session.commit()
