from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.session import flip_missed, get_session, get_sessions_in_range, set_session_status
from app.models import ProgramStatus, SessionStatus, Workout, WorkoutProgram, WorkoutSession
from app.services.program.scheduling import materialize_sessions, session_date, weekday_offsets


@pytest.mark.parametrize(
    "days,expected",
    [
        (1, [0]),
        (2, [0, 3]),
        (3, [0, 2, 4]),
        (4, [0, 1, 3, 4]),
        (5, [0, 1, 2, 3, 4]),
        (6, [0, 1, 2, 3, 4, 5]),
        (7, [0, 1, 2, 3, 4, 5, 6]),
    ],
)
def test_weekday_offsets(days: int, expected: list[int]) -> None:
    assert weekday_offsets(days) == expected


@pytest.mark.parametrize("days", [0, 8, -1])
def test_weekday_offsets_rejects_out_of_range(days: int) -> None:
    with pytest.raises(ValueError):
        weekday_offsets(days)


def test_session_date_first_session_is_the_start_date() -> None:
    offsets = weekday_offsets(3)
    assert session_date(date(2026, 7, 27), 1, 0, offsets) == date(2026, 7, 27)


def test_session_date_spreads_within_the_first_week() -> None:
    offsets = weekday_offsets(3)
    start = date(2026, 7, 27)  # a Monday
    assert session_date(start, 1, 1, offsets) == date(2026, 7, 29)
    assert session_date(start, 1, 2, offsets) == date(2026, 7, 31)


def test_session_date_advances_seven_days_per_week() -> None:
    offsets = weekday_offsets(3)
    start = date(2026, 7, 27)
    assert session_date(start, 3, 0, offsets) == date(2026, 8, 10)


def test_session_date_crosses_a_month_boundary() -> None:
    offsets = weekday_offsets(4)
    start = date(2026, 7, 27)
    assert session_date(start, 2, 3, offsets) == date(2026, 8, 7)


@pytest_asyncio.fixture
async def three_day_program(db_session: AsyncSession) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Test Program",
        status=ProgramStatus.DRAFT,
        duration_weeks=4,
        days_per_week=3,
        start_date=date(2026, 7, 27),
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()
    for order, key in enumerate(["a", "b", "c"]):
        db_session.add(Workout(program_id=program.id, key=key, name=f"Day {key.upper()}", order=order))
    await db_session.commit()
    await db_session.refresh(program, ["workouts"])
    return program


@pytest.mark.asyncio
async def test_materialize_creates_a_row_per_week_and_workout(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    created = await materialize_sessions(db_session, three_day_program)

    assert len(created) == 12
    assert {s.status for s in created} == {SessionStatus.SCHEDULED}
    assert {s.week for s in created} == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_materialize_dates_follow_the_offset_table(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    result = await db_session.execute(
        select(WorkoutSession).where(WorkoutSession.week == 1).order_by(WorkoutSession.scheduled_date)
    )
    dates = [s.scheduled_date for s in result.scalars().all()]

    assert dates == [date(2026, 7, 27), date(2026, 7, 29), date(2026, 7, 31)]


@pytest.mark.asyncio
async def test_materialize_records_the_offsets_on_the_program(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    assert three_day_program.constraints["training_day_offsets"] == [0, 2, 4]


@pytest.mark.asyncio
async def test_materialize_is_idempotent(db_session: AsyncSession, three_day_program: WorkoutProgram) -> None:
    await materialize_sessions(db_session, three_day_program)
    second = await materialize_sessions(db_session, three_day_program)

    assert second == []
    result = await db_session.execute(select(WorkoutSession))
    assert len(list(result.scalars().all())) == 12


@pytest.mark.asyncio
async def test_materialize_skips_a_program_without_a_start_date(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    three_day_program.start_date = None

    assert await materialize_sessions(db_session, three_day_program) == []


@pytest.mark.asyncio
async def test_accepting_a_program_materializes_its_sessions(
    authenticated_client, db_session: AsyncSession, seeded_templates, seeded_exercises, user_environment
) -> None:
    draft = await authenticated_client.post(
        "/api/v1/programs/draft",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general_fitness",
            "weight_unit": "kg",
            "duration_weeks": 4,
            "template_id": 1,
            "required_inputs": {},
            "progression_style": "consistent",
            "effort_method": "rpe",
            "start_date": "2026-07-27",
        },
    )
    program_id = draft.json()["program_id"]

    response = await authenticated_client.post(f"/api/v1/programs/{program_id}/accept")
    assert response.status_code == 200

    result = await db_session.execute(select(WorkoutSession).where(WorkoutSession.program_id == program_id))
    sessions = list(result.scalars().all())
    assert len(sessions) == 12
    assert min(s.scheduled_date for s in sessions) == date(2026, 7, 27)


@pytest.mark.asyncio
async def test_flip_marks_past_scheduled_sessions_missed(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    result = await db_session.execute(select(WorkoutSession).where(WorkoutSession.program_id == three_day_program.id))
    by_date = {s.scheduled_date: s.status for s in result.scalars().all()}

    assert by_date[date(2026, 7, 27)] == SessionStatus.MISSED
    assert by_date[date(2026, 7, 29)] == SessionStatus.MISSED
    assert by_date[date(2026, 7, 31)] == SessionStatus.SCHEDULED


@pytest.mark.asyncio
async def test_flip_leaves_an_abandoned_in_progress_session_alone(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)
    abandoned = next(s for s in sessions if s.scheduled_date == date(2026, 7, 27))
    abandoned.status = SessionStatus.IN_PROGRESS
    await db_session.commit()

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    await db_session.refresh(abandoned)
    assert abandoned.status == SessionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_flip_leaves_completed_sessions_alone(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)
    done = next(s for s in sessions if s.scheduled_date == date(2026, 7, 27))
    done.status = SessionStatus.COMPLETED
    await db_session.commit()

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    await db_session.refresh(done)
    assert done.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_flip_does_not_touch_todays_session(db_session: AsyncSession, three_day_program: WorkoutProgram) -> None:
    await materialize_sessions(db_session, three_day_program)

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 27))

    result = await db_session.execute(select(WorkoutSession).where(WorkoutSession.program_id == three_day_program.id))
    assert {s.status for s in result.scalars().all()} == {SessionStatus.SCHEDULED}


@pytest.mark.asyncio
async def test_range_query_returns_only_sessions_in_the_window(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    three_day_program.user_id = 1
    # get_sessions_in_range only considers ACTIVE programs (archived/draft programs'
    # sessions shouldn't bleed into /schedule) - this test is about window filtering,
    # not program status, so make the fixture program active.
    three_day_program.status = ProgramStatus.ACTIVE
    await materialize_sessions(db_session, three_day_program)

    found = await get_sessions_in_range(db_session, 1, date(2026, 7, 27), date(2026, 8, 2))

    assert [s.scheduled_date for s in found] == [
        date(2026, 7, 27),
        date(2026, 7, 29),
        date(2026, 7, 31),
    ]


@pytest.mark.asyncio
async def test_range_query_excludes_another_users_sessions(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    assert await get_sessions_in_range(db_session, 999, date(2026, 1, 1), date(2027, 1, 1)) == []


@pytest.mark.asyncio
async def test_get_session_is_scoped_to_the_owner(db_session: AsyncSession, three_day_program: WorkoutProgram) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)

    assert await get_session(db_session, sessions[0].id, 1) is not None
    assert await get_session(db_session, sessions[0].id, 999) is None


@pytest.mark.asyncio
async def test_completing_a_session_stamps_completed_at(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)

    updated = await set_session_status(db_session, sessions[0], SessionStatus.COMPLETED)

    assert updated.status == SessionStatus.COMPLETED
    assert updated.completed_at is not None
