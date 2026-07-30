from datetime import date
from typing import Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logging import UserWorkoutLog, WorkoutSetLog
from app.models.session import WorkoutSession
from app.models.user import _utcnow
from app.schemas.logging import UserWorkoutLogCreate
from app.schemas.session import SessionSetLogCreate


def _dedupe_latest_per_set(logs: list[WorkoutSetLog]) -> list[WorkoutSetLog]:
    """Keep only the highest-id row per (session_id, workout_exercise_id, set_number).

    A correction is a second insert for the same set within the same session, so the highest id is always
    the current value; older rows stay in the table for audit but are never
    surfaced. Relies on dict insertion order to preserve each query's own
    ORDER BY - the first time a key is seen fixes its position, and overwriting
    the value for that key later doesn't move it.
    """
    best: dict[tuple[int, int, int], WorkoutSetLog] = {}
    for log in logs:
        key = (log.session_id, log.workout_exercise_id, log.set_number)
        current = best.get(key)
        if current is None or log.id > current.id:
            best[key] = log
    return list(best.values())


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
    """Get all set logs for a workout session, ordered by set_number, deduped to the latest value per set."""
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
    return _dedupe_latest_per_set(list(result.scalars().all()))


async def get_set_logs_for_sessions(
    db: AsyncSession, program_id: int, user_id: int, since: date
) -> list[WorkoutSetLog]:
    """Set logs for one program's sessions, windowed to the reactive-deload lookback,
    deduped to the latest value per set.

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
        .order_by(WorkoutSetLog.session_id, WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))


async def get_all_set_logs_for_program(db: AsyncSession, program_id: int, user_id: int) -> list[WorkoutSetLog]:
    """All of a user's set logs for one program, unwindowed, deduped to the latest value per set.

    Backs the dashboard stats cards (personal records, total volume), which need
    full history rather than the reactive-deload lookback window.
    """
    stmt = (
        select(WorkoutSetLog)
        .join(WorkoutSession, WorkoutSession.id == WorkoutSetLog.session_id)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                WorkoutSetLog.user_id == user_id,
            )
        )
        .order_by(WorkoutSetLog.session_id, WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))


async def get_set_logs_for_session(db: AsyncSession, session_id: int, user_id: int) -> list[WorkoutSetLog]:
    """Set logs for a single session, deduped to the latest value per set.

    This is what session-detail responses (and thus the frontend's logged_sets)
    are built from.
    """
    stmt = (
        select(WorkoutSetLog)
        .where(
            and_(
                WorkoutSetLog.session_id == session_id,
                WorkoutSetLog.user_id == user_id,
            )
        )
        .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))


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
