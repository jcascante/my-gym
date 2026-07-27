from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.crud import logging as crud_logging
from app.crud.session import get_session, get_sessions_in_range, set_session_status
from app.models.logging import UserWorkoutLog, WorkoutSetLog
from app.models.program import Workout
from app.models.session import SessionStatus, WorkoutSession
from app.models.user import User
from app.schemas.logging import UserWorkoutLogCreate, UserWorkoutLogOut, WorkoutSetLogOut
from app.schemas.program_api import WorkoutPreviewOut
from app.schemas.session import ScheduleEntryOut, SessionDetailOut, SessionSetLogCreate
from app.services.program.loading import load_program_with_definition
from app.services.program.preview import derive_week

router = APIRouter(prefix="/users/me", tags=["sessions"])

DEFAULT_DURATION_MIN = 45


async def _workouts_by_id(db: AsyncSession, workout_ids: list[int]) -> dict[int, Workout]:
    if not workout_ids:
        return {}
    result = await db.execute(
        select(Workout).where(Workout.id.in_(workout_ids)).options(selectinload(Workout.exercises))
    )
    return {workout.id: workout for workout in result.scalars().all()}


async def _workout_for(db: AsyncSession, session: WorkoutSession) -> Workout:
    workouts = await _workouts_by_id(db, [session.workout_id])
    workout = workouts.get(session.workout_id)
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


def _duration_for(user: User) -> int:
    # get_user_by_id selectinloads User.profile, so this never lazy-loads.
    return (user.profile.workout_duration_min if user.profile else None) or DEFAULT_DURATION_MIN


@router.get("/schedule", response_model=list[ScheduleEntryOut])
async def list_schedule(
    start: date,
    end: date,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduleEntryOut]:
    sessions = await get_sessions_in_range(db, user.id, start, end)
    duration_min = _duration_for(user)
    workouts = await _workouts_by_id(db, [s.workout_id for s in sessions])

    return [
        ScheduleEntryOut(
            session_id=session.id,
            scheduled_date=session.scheduled_date,
            week=session.week,
            status=session.status.value,
            workout_id=session.workout_id,
            workout_name=workouts[session.workout_id].name,
            exercise_count=len(workouts[session.workout_id].exercises),
            duration_min=duration_min,
        )
        for session in sessions
        if session.workout_id in workouts
    ]


async def _owned_session(db: AsyncSession, session_id: int, user: User) -> WorkoutSession:
    session = await get_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _session_detail(db: AsyncSession, session: WorkoutSession, user: User) -> SessionDetailOut:
    workout = await _workout_for(db, session)
    program, definition = await load_program_with_definition(db, user.id, session.program_id)
    week_days = derive_week(program, definition, session.week)
    day = next((d for d in week_days if d["workout_id"] == session.workout_id), None)
    preview = WorkoutPreviewOut(**day) if day else None

    logs = (
        (
            await db.execute(
                select(WorkoutSetLog)
                .where(WorkoutSetLog.session_id == session.id)
                .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
            )
        )
        .scalars()
        .all()
    )

    return SessionDetailOut(
        session_id=session.id,
        scheduled_date=session.scheduled_date,
        week=session.week,
        status=session.status.value,
        completed_at=session.completed_at,
        workout_id=workout.id,
        workout_name=workout.name,
        exercise_count=len(workout.exercises),
        duration_min=_duration_for(user),
        program_id=program.id,
        program_name=program.name,
        slots=preview.slots if preview else [],
        logged_sets=[WorkoutSetLogOut.model_validate(log) for log in logs],
        reactive_deload=preview.reactive_deload if preview else False,
        deload_reason=preview.deload_reason if preview else None,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
async def get_session_detail(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailOut:
    return await _session_detail(db, await _owned_session(db, session_id, user), user)


@router.post(
    "/sessions/{session_id}/set-logs",
    response_model=WorkoutSetLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_set_log(
    session_id: int,
    data: SessionSetLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSetLog:
    session = await _owned_session(db, session_id, user)

    log = await crud_logging.append_set_log(db, user.id, session, data)

    if session.status == SessionStatus.SCHEDULED:
        await set_session_status(db, session, SessionStatus.IN_PROGRESS)

    return log


@router.post(
    "/sessions/{session_id}/readiness",
    response_model=UserWorkoutLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_readiness(
    session_id: int,
    data: UserWorkoutLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkoutLog:
    session = await _owned_session(db, session_id, user)
    return await crud_logging.create_workout_log(db, user.id, session, data)


@router.post("/sessions/{session_id}/complete", response_model=SessionDetailOut)
async def complete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailOut:
    session = await _owned_session(db, session_id, user)

    if session.status != SessionStatus.COMPLETED:
        await set_session_status(db, session, SessionStatus.COMPLETED)

    return await _session_detail(db, session, user)
