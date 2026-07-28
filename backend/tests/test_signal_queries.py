from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.logging import get_readiness_for_sessions, get_set_logs_for_sessions
from app.models import (
    ProgramStatus,
    User,
    UserWorkoutLog,
    Workout,
    WorkoutProgram,
    WorkoutSession,
    WorkoutSetLog,
)
from app.services.program.scheduling import materialize_sessions


async def _program(db: AsyncSession, user_id: int, name: str) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=user_id,
        template_id=1,
        environment_id=1,
        name=name,
        status=ProgramStatus.ACTIVE,
        duration_weeks=2,
        days_per_week=1,
        start_date=date.today(),
        constraints={},
    )
    db.add(program)
    await db.flush()
    db.add(Workout(program_id=program.id, key="a", name="Day A", order=0))
    await db.commit()
    await db.refresh(program, ["workouts"])
    await materialize_sessions(db, program)
    return program


@pytest_asyncio.fixture
async def two_programs(db_session: AsyncSession, test_user: User) -> tuple[WorkoutProgram, WorkoutProgram]:
    return await _program(db_session, test_user.id, "A"), await _program(db_session, test_user.id, "B")


async def _log_set(db: AsyncSession, user_id: int, session: WorkoutSession, rpe: float) -> None:
    db.add(
        WorkoutSetLog(
            user_id=user_id,
            session_id=session.id,
            workout_id=session.workout_id,
            workout_exercise_id=1,
            set_number=1,
            actual_rpe=rpe,
            effort_method="rpe",
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_set_logs_are_scoped_to_one_program(
    db_session: AsyncSession, test_user: User, two_programs: tuple[WorkoutProgram, WorkoutProgram]
) -> None:
    program_a, program_b = two_programs
    sessions_a = (
        await db_session.execute(WorkoutSession.__table__.select().where(WorkoutSession.program_id == program_a.id))
    ).fetchall()
    session_a_id = sessions_a[0].id
    session_a = await db_session.get(WorkoutSession, session_a_id)
    assert session_a is not None
    await _log_set(db_session, test_user.id, session_a, 8.0)

    from_a = await get_set_logs_for_sessions(db_session, program_a.id, test_user.id, date.today() - timedelta(days=14))
    from_b = await get_set_logs_for_sessions(db_session, program_b.id, test_user.id, date.today() - timedelta(days=14))

    assert len(from_a) == 1
    assert from_b == []


@pytest.mark.asyncio
async def test_set_logs_exclude_another_user(
    db_session: AsyncSession, test_user: User, two_programs: tuple[WorkoutProgram, WorkoutProgram]
) -> None:
    program_a, _ = two_programs
    session = (
        await db_session.execute(WorkoutSession.__table__.select().where(WorkoutSession.program_id == program_a.id))
    ).fetchall()[0]
    resolved = await db_session.get(WorkoutSession, session.id)
    assert resolved is not None
    await _log_set(db_session, test_user.id, resolved, 8.0)

    assert await get_set_logs_for_sessions(db_session, program_a.id, 999, date.today() - timedelta(days=14)) == []


@pytest.mark.asyncio
async def test_readiness_is_scoped_to_one_program(
    db_session: AsyncSession, test_user: User, two_programs: tuple[WorkoutProgram, WorkoutProgram]
) -> None:
    program_a, program_b = two_programs
    session = (
        await db_session.execute(WorkoutSession.__table__.select().where(WorkoutSession.program_id == program_a.id))
    ).fetchall()[0]
    resolved = await db_session.get(WorkoutSession, session.id)
    assert resolved is not None
    db_session.add(
        UserWorkoutLog(
            user_id=test_user.id,
            session_id=resolved.id,
            workout_id=resolved.workout_id,
            session_date=datetime.now(),
            readiness=2,
        )
    )
    await db_session.commit()

    since = date.today() - timedelta(days=14)
    assert len(await get_readiness_for_sessions(db_session, program_a.id, test_user.id, since)) == 1
    assert await get_readiness_for_sessions(db_session, program_b.id, test_user.id, since) == []
