from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.crud import logging as crud_logging
from app.models.logging import UserWorkoutLog, WorkoutSetLog
from app.models.user import User
from app.schemas.logging import (
    UserWorkoutLogCreate,
    UserWorkoutLogOut,
    WorkoutSetLogCreate,
    WorkoutSetLogOut,
)

router = APIRouter(prefix="/workouts", tags=["logging"])


@router.post("/{workout_id}/logs", response_model=UserWorkoutLogOut, status_code=status.HTTP_201_CREATED)
async def create_session_log(
    workout_id: int,
    data: UserWorkoutLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkoutLog:
    """Create a new workout session log (start of workout)."""
    # Verify workout_id in data matches route param
    if data.workout_id != workout_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workout_id mismatch")

    log = await crud_logging.create_workout_log(db, user.id, data)
    return log


@router.get("/logs", response_model=list[UserWorkoutLogOut])
async def list_user_logs(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserWorkoutLog]:
    """List user's workout session logs."""
    logs = await crud_logging.get_user_workout_logs(db, user.id, limit=limit, offset=offset)
    return logs


@router.get("/{workout_id}/logs/{log_id}", response_model=UserWorkoutLogOut)
async def get_session_log(
    workout_id: int,
    log_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkoutLog:
    """Get a specific workout session log."""
    log = await crud_logging.get_workout_log(db, log_id, user.id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return log


@router.post("/{workout_id}/sets", response_model=WorkoutSetLogOut, status_code=status.HTTP_201_CREATED)
async def append_set_log(
    workout_id: int,
    data: WorkoutSetLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSetLog:
    """Append a new set log during/after workout completion."""
    if data.workout_id != workout_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workout_id mismatch")

    log = await crud_logging.append_set_log(db, user.id, data)
    return log


@router.get("/{workout_id}/sets", response_model=list[WorkoutSetLogOut])
async def get_workout_sets(
    workout_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkoutSetLog]:
    """Get all set logs for a workout session."""
    logs = await crud_logging.get_set_logs(db, workout_id, user.id)
    return logs
