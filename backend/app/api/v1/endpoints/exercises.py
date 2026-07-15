from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import ExerciseNotFoundError
from app.core.database import get_db
from app.crud.exercise import get_exercise, list_exercises
from app.models import BodyRegion, Exercise, ExperienceLevel, MovementPattern, User
from app.schemas import ExerciseResponse

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseResponse])
async def list_exercises_endpoint(
    body_region: BodyRegion | None = None,
    movement_pattern: MovementPattern | None = None,
    muscle_group: str | None = None,
    equipment_tags: list[str] = Query([]),
    difficulty_level: ExperienceLevel | None = None,
    exclude_contraindications: list[str] = Query([]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Exercise]:
    exercises = await list_exercises(
        db,
        body_region=body_region,
        movement_pattern=movement_pattern,
        muscle_group=muscle_group,
        equipment_tags=equipment_tags or None,
        difficulty_level=difficulty_level,
        exclude_contraindications=exclude_contraindications or None,
    )
    return exercises


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise_endpoint(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Exercise:
    exercise = await get_exercise(db, exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError()
    return exercise
