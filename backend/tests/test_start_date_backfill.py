from datetime import date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramStatus, User, WorkoutProgram

_BACKFILL_SQL = "UPDATE workout_programs SET start_date = date(created_at) WHERE start_date IS NULL"


async def _make_program(
    db_session: AsyncSession, user: User, *, start_date: date | None, created_at: datetime
) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=user.id,
        template_id=1,
        environment_id=1,
        name="Backfill Test",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=3,
        start_date=start_date,
        weight_unit="kg",
        constraints={},
        created_at=created_at,
    )
    db_session.add(program)
    await db_session.commit()
    await db_session.refresh(program)
    return program


@pytest.mark.asyncio
async def test_backfill_sets_start_date_from_created_at_only_when_null(db_session: AsyncSession, test_user: User):
    needs_backfill = await _make_program(
        db_session, test_user, start_date=None, created_at=datetime(2026, 3, 15, 10, 30)
    )
    already_set = await _make_program(
        db_session, test_user, start_date=date(2026, 6, 1), created_at=datetime(2026, 1, 1)
    )

    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()

    await db_session.refresh(needs_backfill)
    await db_session.refresh(already_set)
    assert needs_backfill.start_date == date(2026, 3, 15)
    assert already_set.start_date == date(2026, 6, 1)


@pytest.mark.asyncio
async def test_backfill_is_idempotent(db_session: AsyncSession, test_user: User):
    program = await _make_program(db_session, test_user, start_date=None, created_at=datetime(2026, 3, 15, 10, 30))

    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()
    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()

    await db_session.refresh(program)
    assert program.start_date == date(2026, 3, 15)
