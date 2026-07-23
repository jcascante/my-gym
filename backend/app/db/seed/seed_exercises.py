import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.db.seed.exercise_classification import classify_exercise, derive_provocation_tags, validate_tags
from app.db.seed.exercises import EXERCISE_SEED_DATA
from app.models import Exercise


async def upsert_exercises(db: AsyncSession) -> None:
    """Upsert exercises from seed data. Deactivates exercises no longer in seed."""
    seed_slugs: set[str] = {str(ex["slug"]) for ex in EXERCISE_SEED_DATA}

    for data in EXERCISE_SEED_DATA:
        validate_tags(data)
        is_unilateral, is_compound = classify_exercise(data)
        provocation_tags = derive_provocation_tags(data)
        row = {
            **data,
            "is_unilateral": is_unilateral,
            "is_compound": is_compound,
            "provocation_tags": provocation_tags,
        }

        existing = await db.execute(select(Exercise).where(Exercise.slug == data["slug"]))
        exercise = existing.scalar_one_or_none()

        if exercise is None:
            exercise = Exercise(**row, is_active=True)
            db.add(exercise)
        else:
            for key, value in row.items():
                setattr(exercise, key, value)
            exercise.is_active = True
            db.add(exercise)

    await db.flush()

    # Deactivate exercises no longer in seed
    existing_exercises = await db.execute(select(Exercise))
    for exercise in existing_exercises.scalars().all():
        if exercise.slug not in seed_slugs and exercise.is_active:
            exercise.is_active = False
            db.add(exercise)

    await db.commit()


async def main() -> None:
    async with async_session() as db:
        await upsert_exercises(db)
        print("Exercise seed data upserted successfully")


if __name__ == "__main__":
    asyncio.run(main())
