from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TrainingEnvironment


async def list_training_environments(db: AsyncSession, user_id: int) -> list[TrainingEnvironment]:
    result = await db.execute(select(TrainingEnvironment).where(TrainingEnvironment.user_id == user_id))
    return list(result.scalars().all())


async def get_training_environment(db: AsyncSession, user_id: int, environment_id: int) -> TrainingEnvironment | None:
    result = await db.execute(
        select(TrainingEnvironment).where(
            TrainingEnvironment.id == environment_id,
            TrainingEnvironment.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _clear_existing_default(db: AsyncSession, user_id: int, exclude_id: int | None = None) -> None:
    existing = await list_training_environments(db, user_id)
    for environment in existing:
        if environment.is_default and environment.id != exclude_id:
            environment.is_default = False
            db.add(environment)


async def create_training_environment(db: AsyncSession, user_id: int, data: dict[str, Any]) -> TrainingEnvironment:
    if data.get("is_default"):
        await _clear_existing_default(db, user_id)

    environment = TrainingEnvironment(user_id=user_id, **data)
    db.add(environment)
    await db.flush()
    await db.commit()
    await db.refresh(environment)
    return environment


async def update_training_environment(
    db: AsyncSession, environment: TrainingEnvironment, data: dict[str, Any]
) -> TrainingEnvironment:
    if data.get("is_default"):
        await _clear_existing_default(db, environment.user_id, exclude_id=environment.id)

    for key, value in data.items():
        setattr(environment, key, value)
    db.add(environment)

    await db.flush()
    await db.commit()
    await db.refresh(environment)
    return environment


async def delete_training_environment(db: AsyncSession, environment: TrainingEnvironment) -> None:
    await db.delete(environment)
    await db.commit()
