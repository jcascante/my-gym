from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InjuryRecord


async def list_injury_records(db: AsyncSession, user_id: int) -> list[InjuryRecord]:
    result = await db.execute(select(InjuryRecord).where(InjuryRecord.user_id == user_id))
    return list(result.scalars().all())


async def get_injury_record(db: AsyncSession, user_id: int, injury_id: int) -> InjuryRecord | None:
    result = await db.execute(
        select(InjuryRecord).where(
            InjuryRecord.id == injury_id,
            InjuryRecord.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_injury_record(db: AsyncSession, user_id: int, data: dict[str, Any]) -> InjuryRecord:
    injury_record = InjuryRecord(user_id=user_id, **data)
    db.add(injury_record)
    await db.flush()
    await db.commit()
    await db.refresh(injury_record)
    return injury_record


async def update_injury_record(db: AsyncSession, injury_record: InjuryRecord, data: dict[str, Any]) -> InjuryRecord:
    for key, value in data.items():
        setattr(injury_record, key, value)
    db.add(injury_record)

    await db.flush()
    await db.commit()
    await db.refresh(injury_record)
    return injury_record


async def delete_injury_record(db: AsyncSession, injury_record: InjuryRecord) -> None:
    await db.delete(injury_record)
    await db.commit()
