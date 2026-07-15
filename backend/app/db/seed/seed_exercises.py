import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.db.seed.exercises import EXERCISE_SEED_DATA
from app.models import Exercise


async def upsert_exercises(db: AsyncSession) -> None:
    """Upsert exercises from seed data. Deactivates exercises no longer in seed."""
    seed_slugs: set[str] = {str(ex["slug"]) for ex in EXERCISE_SEED_DATA}

    for data in EXERCISE_SEED_DATA:
        existing = await db.execute(select(Exercise).where(Exercise.slug == data["slug"]))
        exercise = existing.scalar_one_or_none()

        if exercise is None:
            exercise = Exercise(**data, is_active=True)
            db.add(exercise)
        else:
            for key, value in data.items():
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
