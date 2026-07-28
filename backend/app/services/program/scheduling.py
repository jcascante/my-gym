from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.program import WorkoutProgram
from app.models.session import SessionStatus, WorkoutSession

# Day offsets from the program's start weekday, spread to leave rest days where
# the week allows it. Keyed by sessions per week.
_OFFSETS: dict[int, list[int]] = {
    1: [0],
    2: [0, 3],
    3: [0, 2, 4],
    4: [0, 1, 3, 4],
    5: [0, 1, 2, 3, 4],
    6: [0, 1, 2, 3, 4, 5],
    7: [0, 1, 2, 3, 4, 5, 6],
}


def weekday_offsets(sessions_per_week: int) -> list[int]:
    if sessions_per_week not in _OFFSETS:
        raise ValueError(f"sessions_per_week must be 1-7, got {sessions_per_week}")
    return list(_OFFSETS[sessions_per_week])


def session_date(start_date: date, week: int, index: int, offsets: list[int]) -> date:
    return start_date + timedelta(days=(week - 1) * 7 + offsets[index])


async def materialize_sessions(db: AsyncSession, program: WorkoutProgram) -> list[WorkoutSession]:
    """Create the dated session rows for a program, once."""
    if program.start_date is None or not program.workouts:
        return []

    existing = await db.execute(select(WorkoutSession.id).where(WorkoutSession.program_id == program.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return []

    workouts = sorted(program.workouts, key=lambda w: w.order)
    offsets = weekday_offsets(len(workouts))

    # Pinned so the dates stay put even if the spread table is later changed.
    program.constraints["training_day_offsets"] = offsets
    flag_modified(program, "constraints")

    sessions = [
        WorkoutSession(
            program_id=program.id,
            workout_id=workout.id,
            week=week,
            scheduled_date=session_date(program.start_date, week, index, offsets),
            status=SessionStatus.SCHEDULED,
        )
        for week in range(1, program.duration_weeks + 1)
        for index, workout in enumerate(workouts)
    ]
    db.add_all(sessions)
    await db.commit()
    return sessions
