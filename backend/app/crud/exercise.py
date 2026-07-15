from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BodyRegion, Exercise, ExperienceLevel, MovementPattern


async def list_exercises(
    db: AsyncSession,
    *,
    body_region: BodyRegion | None = None,
    movement_pattern: MovementPattern | None = None,
    muscle_group: str | None = None,
    equipment_tags: list[str] | None = None,
    difficulty_level: ExperienceLevel | None = None,
    exclude_contraindications: list[str] | None = None,
) -> list[Exercise]:
    query = select(Exercise).where(Exercise.is_active.is_(True))

    if body_region is not None:
        query = query.where(Exercise.body_region == body_region)

    if movement_pattern is not None:
        query = query.where(Exercise.movement_pattern == movement_pattern)

    if difficulty_level is not None:
        query = query.where(Exercise.difficulty_level == difficulty_level)

    result = await db.execute(query)
    exercises = list(result.scalars().all())

    if muscle_group is not None:
        exercises = [
            ex for ex in exercises if muscle_group in ex.primary_muscles or muscle_group in ex.secondary_muscles
        ]

    if equipment_tags:
        equipment_set = set(equipment_tags)
        exercises = [ex for ex in exercises if set(ex.equipment_tags).issubset(equipment_set)]

    if exclude_contraindications:
        contraindications_set = set(exclude_contraindications)
        exercises = [ex for ex in exercises if not contraindications_set.intersection(set(ex.contraindications))]

    return exercises


async def get_exercise(db: AsyncSession, exercise_id: int) -> Exercise | None:
    result = await db.execute(
        select(Exercise).where(
            Exercise.id == exercise_id,
            Exercise.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
