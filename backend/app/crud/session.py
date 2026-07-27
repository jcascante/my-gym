from datetime import date

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program import WorkoutProgram
from app.models.session import SessionStatus, WorkoutSession
from app.models.user import _utcnow


async def flip_missed(db: AsyncSession, program_id: int, today: date) -> None:
    """Age out past sessions the user never started.

    Only SCHEDULED rows move, so a session left IN_PROGRESS stays that way
    rather than being reported as never attempted.
    """
    await db.execute(
        update(WorkoutSession)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                WorkoutSession.status == SessionStatus.SCHEDULED,
                WorkoutSession.scheduled_date < today,
            )
        )
        .values(status=SessionStatus.MISSED)
    )
    await db.commit()


async def get_sessions_in_range(db: AsyncSession, user_id: int, start: date, end: date) -> list[WorkoutSession]:
    program_ids = (await db.execute(select(WorkoutProgram.id).where(WorkoutProgram.user_id == user_id))).scalars().all()
    if not program_ids:
        return []

    for program_id in program_ids:
        await flip_missed(db, program_id, date.today())

    result = await db.execute(
        select(WorkoutSession)
        .where(
            and_(
                WorkoutSession.program_id.in_(program_ids),
                WorkoutSession.scheduled_date >= start,
                WorkoutSession.scheduled_date <= end,
            )
        )
        .order_by(WorkoutSession.scheduled_date, WorkoutSession.id)
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: int, user_id: int) -> WorkoutSession | None:
    result = await db.execute(
        select(WorkoutSession)
        .join(WorkoutProgram, WorkoutProgram.id == WorkoutSession.program_id)
        .where(and_(WorkoutSession.id == session_id, WorkoutProgram.user_id == user_id))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    await flip_missed(db, session.program_id, date.today())
    await db.refresh(session)
    return session


async def set_session_status(db: AsyncSession, session: WorkoutSession, status: SessionStatus) -> WorkoutSession:
    session.status = status
    if status == SessionStatus.COMPLETED:
        session.completed_at = _utcnow()
    await db.commit()
    await db.refresh(session)
    return session
