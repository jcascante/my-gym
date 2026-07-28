from datetime import date
from typing import Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logging import UserWorkoutLog, WorkoutSetLog
from app.models.session import WorkoutSession
from app.models.user import _utcnow
from app.schemas.logging import UserWorkoutLogCreate
from app.schemas.session import SessionSetLogCreate


async def append_set_log(
    db: AsyncSession, user_id: int, session: WorkoutSession, data: SessionSetLogCreate
) -> WorkoutSetLog:
    """Append a set log, anchored to the session that produced it."""
    log = WorkoutSetLog(
        user_id=user_id,
        session_id=session.id,
        workout_id=session.workout_id,
        workout_exercise_id=data.workout_exercise_id,
        set_number=data.set_number,
        actual_weight=data.actual_weight,
        actual_reps=data.actual_reps,
        actual_rpe=data.actual_rpe,
        effort_method=data.effort_method,
    )
    db.add(log)
    await db.flush()
    await db.commit()
    await db.refresh(log)
    return log


async def create_workout_log(
    db: AsyncSession, user_id: int, session: WorkoutSession, data: UserWorkoutLogCreate
) -> UserWorkoutLog:
    """Create a readiness log, anchored to the session it describes."""
    log = UserWorkoutLog(
        user_id=user_id,
        session_id=session.id,
        workout_id=session.workout_id,
        session_date=_utcnow(),
        readiness=data.readiness,
        notes=data.notes,
    )
    db.add(log)
    await db.flush()
    await db.commit()
    await db.refresh(log)
    return log


async def get_workout_log(db: AsyncSession, log_id: int, user_id: int) -> Optional[UserWorkoutLog]:
    """Get a specific workout log, scoped to user."""
    stmt = select(UserWorkoutLog).where(and_(UserWorkoutLog.id == log_id, UserWorkoutLog.user_id == user_id))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_workout_logs(
    db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0
) -> list[UserWorkoutLog]:
    """Get user's workout logs, ordered by session_date descending."""
    stmt = (
        select(UserWorkoutLog)
        .where(UserWorkoutLog.user_id == user_id)
        .order_by(desc(UserWorkoutLog.session_date))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_set_logs(db: AsyncSession, workout_id: int, user_id: int) -> list[WorkoutSetLog]:
    """Get all set logs for a workout session, ordered by set_number."""
    stmt = (
        select(WorkoutSetLog)
        .where(
            and_(
                WorkoutSetLog.workout_id == workout_id,
                WorkoutSetLog.user_id == user_id,
            )
        )
        .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_set_logs_for_sessions(
    db: AsyncSession, program_id: int, user_id: int, since: date
) -> list[WorkoutSetLog]:
    """Set logs for one program's sessions, windowed to the reactive-deload lookback.

    Joining through workout_sessions is what scopes this to a single program -
    workout_id alone is shared across every week of the program that owns it.
    """
    stmt = (
        select(WorkoutSetLog)
        .join(WorkoutSession, WorkoutSession.id == WorkoutSetLog.session_id)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                WorkoutSetLog.user_id == user_id,
                WorkoutSetLog.created_at >= since,
            )
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_readiness_for_sessions(
    db: AsyncSession, program_id: int, user_id: int, since: date
) -> list[UserWorkoutLog]:
    """Readiness logs for one program's sessions, for the reactive-deload window."""
    stmt = (
        select(UserWorkoutLog)
        .join(WorkoutSession, WorkoutSession.id == UserWorkoutLog.session_id)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                UserWorkoutLog.user_id == user_id,
                UserWorkoutLog.session_date >= since,
            )
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
