from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.programs import _preview_out
from app.crud.program import get_program
from app.models import (
    ProgramStatus,
    ProgramTemplate,
    SessionStatus,
    User,
    UserWorkoutLog,
    Workout,
    WorkoutExercise,
    WorkoutProgram,
    WorkoutSession,
    WorkoutSetLog,
)
from app.schemas.template import TemplateDefinition
from app.services.program.scheduling import materialize_sessions


async def _build_program(
    db_session: AsyncSession,
    test_user: User,
    template: ProgramTemplate,
    *,
    status: ProgramStatus,
    start_date: date | None,
    duration_weeks: int = 8,
) -> tuple[WorkoutProgram, Workout, WorkoutExercise, WorkoutSession]:
    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=template.id,
        environment_id=1,
        name="Live Signal Test",
        status=status,
        duration_weeks=duration_weeks,
        days_per_week=3,
        start_date=start_date,
        weight_unit="kg",
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="day_a", name="Day A", order=1)
    db_session.add(workout)
    await db_session.flush()

    exercise = WorkoutExercise(
        workout_id=workout.id,
        order=1,
        exercise_id=1,
        fills_rule={"priority": "primary"},
        sets=3,
        reps_min=5,
        reps_max=5,
        base_load=100.0,
        rest_seconds=120,
        scheme_key="main",
        target_rpe=8.0,
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(exercise)
    await db_session.commit()

    saved = await get_program(db_session, test_user.id, program.id)
    assert saved is not None

    # materialize_sessions is a no-op without a start_date; these fixtures still
    # need a real session row to satisfy session_id NOT NULL, so build one by hand
    # when there's no date to schedule against (current_week is None regardless).
    if start_date is not None:
        await materialize_sessions(db_session, saved)
        result = await db_session.execute(
            select(WorkoutSession).where(WorkoutSession.program_id == saved.id).order_by(WorkoutSession.week)
        )
        session = result.scalars().first()
        assert session is not None
    else:
        session = WorkoutSession(
            program_id=saved.id,
            workout_id=workout.id,
            week=1,
            scheduled_date=date.today(),
            status=SessionStatus.SCHEDULED,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

    return saved, workout, exercise, session


async def _add_high_rpe_set_logs(
    db_session: AsyncSession, test_user: User, session: WorkoutSession, exercise: WorkoutExercise
) -> list[int]:
    """Create logs at multiple time points (different sessions) with high RPE.
    Returns the list of session IDs used. Uses different sessions for each time point."""
    # Query for sessions in this program, ordered by week ascending to get different weeks
    result = await db_session.execute(
        select(WorkoutSession)
        .where(WorkoutSession.program_id == session.program_id)
        .order_by(WorkoutSession.week.asc())
        .limit(3)
    )
    available_sessions = list(result.scalars().all())

    session_ids = []
    for idx, days_ago in enumerate((2, 5), 1):
        # Use different sessions for different time points (week by week)
        sess = available_sessions[min(idx, len(available_sessions) - 1)]
        session_ids.append(sess.id)

        db_session.add(
            WorkoutSetLog(
                user_id=test_user.id,
                session_id=sess.id,
                workout_id=sess.workout_id,
                workout_exercise_id=exercise.id,
                set_number=idx,
                actual_weight=100.0,
                actual_reps=5,
                actual_rpe=9.5,
                effort_method="rpe",
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            )
        )
    await db_session.commit()
    return session_ids


async def _add_low_readiness_logs(
    db_session: AsyncSession, test_user: User, session_ids: list[int], workout_id: int
) -> None:
    for session_id, days_ago in zip(session_ids, (2, 5)):
        db_session.add(
            UserWorkoutLog(
                user_id=test_user.id,
                session_id=session_id,
                workout_id=workout_id,
                session_date=datetime.utcnow() - timedelta(days=days_ago),
                readiness=1,
            )
        )
    await db_session.commit()


@pytest.mark.asyncio
async def test_current_week_gets_live_signals_but_adjacent_weeks_stay_nominal(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=2)  # lands on week 3 of an 8-week program
    program, workout, exercise, session = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week == 3

    current = result.weeks[3][0]
    assert current.slots[0].adjustment_reason is not None
    assert current.reactive_deload is True
    assert current.deload_reason is not None

    for week in (2, 4):
        day = result.weeks[week][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False
        assert day.deload_reason is None


@pytest.mark.asyncio
async def test_draft_and_archived_programs_never_get_live_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=2)
    for status in (ProgramStatus.DRAFT, ProgramStatus.ARCHIVED):
        program, workout, exercise, session = await _build_program(
            db_session, test_user, sample_template_orm, status=status, start_date=start_date
        )
        session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
        await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        result = await _preview_out(db_session, program, definition, test_user)

        assert result.current_week is None

        day = result.weeks[3][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_future_start_date_yields_no_current_week_and_no_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() + timedelta(days=5)
    program, workout, exercise, session = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week is None

    day = result.weeks[1][0]
    assert day.slots[0].adjustment_reason is None
    assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_overrun_start_date_yields_no_current_week_and_no_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=20)
    program, workout, exercise, session = await _build_program(
        db_session,
        test_user,
        sample_template_orm,
        status=ProgramStatus.ACTIVE,
        start_date=start_date,
        duration_weeks=8,
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week is None

    for week in range(1, 9):
        day = result.weeks[week][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_exact_week_one_boundary_gets_signals_only_on_week_one(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    program, workout, exercise, session = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=date.today()
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week == 1
    assert result.weeks[1][0].slots[0].adjustment_reason is not None
    assert result.weeks[2][0].slots[0].adjustment_reason is None


@pytest.mark.asyncio
async def test_null_start_date_falls_back_to_nominal_without_error(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    program, workout, exercise, session = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=None
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week is None
    day = result.weeks[1][0]
    assert day.slots[0].adjustment_reason is None
    assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_get_program_endpoint_surfaces_live_signals_over_http(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    sample_template_orm: ProgramTemplate,
):
    """End-to-end proof the wiring reaches an actual HTTP response, not just _preview_out."""
    start_date = date.today() - timedelta(weeks=2)  # lands on week 3 of an 8-week program
    program, workout, exercise, session = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    session_ids = await _add_high_rpe_set_logs(db_session, test_user, session, exercise)
    await _add_low_readiness_logs(db_session, test_user, session_ids, workout.id)

    response = await authenticated_client.get(f"/api/v1/programs/{program.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["current_week"] == 3
    current_week_slots = [slot for day in data["weeks"]["3"] for slot in day["slots"]]
    assert any(slot["adjustment_reason"] is not None for slot in current_week_slots)
