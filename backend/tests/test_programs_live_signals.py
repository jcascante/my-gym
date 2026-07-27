from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.programs import _preview_out
from app.crud.program import get_program
from app.models import (
    ProgramStatus,
    ProgramTemplate,
    User,
    UserWorkoutLog,
    Workout,
    WorkoutExercise,
    WorkoutProgram,
    WorkoutSetLog,
)
from app.schemas.template import TemplateDefinition


async def _build_program(
    db_session: AsyncSession,
    test_user: User,
    template: ProgramTemplate,
    *,
    status: ProgramStatus,
    start_date: date | None,
    duration_weeks: int = 8,
) -> tuple[WorkoutProgram, Workout, WorkoutExercise]:
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
    return saved, workout, exercise


async def _add_high_rpe_set_logs(
    db_session: AsyncSession, test_user: User, workout: Workout, exercise: WorkoutExercise
) -> None:
    for days_ago in (2, 5):
        db_session.add(
            WorkoutSetLog(
                user_id=test_user.id,
                workout_id=workout.id,
                workout_exercise_id=exercise.id,
                set_number=1,
                actual_weight=100.0,
                actual_reps=5,
                actual_rpe=9.5,
                effort_method="rpe",
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            )
        )
    await db_session.commit()


async def _add_low_readiness_logs(db_session: AsyncSession, test_user: User, workout: Workout) -> None:
    for days_ago in (2, 5):
        db_session.add(
            UserWorkoutLog(
                user_id=test_user.id,
                workout_id=workout.id,
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
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

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
        program, workout, exercise = await _build_program(
            db_session, test_user, sample_template_orm, status=status, start_date=start_date
        )
        await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
        await _add_low_readiness_logs(db_session, test_user, workout)

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
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

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
    program, workout, exercise = await _build_program(
        db_session,
        test_user,
        sample_template_orm,
        status=ProgramStatus.ACTIVE,
        start_date=start_date,
        duration_weeks=8,
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

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
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=date.today()
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.current_week == 1
    assert result.weeks[1][0].slots[0].adjustment_reason is not None
    assert result.weeks[2][0].slots[0].adjustment_reason is None


@pytest.mark.asyncio
async def test_null_start_date_falls_back_to_nominal_without_error(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=None
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

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
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    response = await authenticated_client.get(f"/api/v1/programs/{program.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["current_week"] == 3
    current_week_slots = [slot for day in data["weeks"]["3"] for slot in day["slots"]]
    assert any(slot["adjustment_reason"] is not None for slot in current_week_slots)
