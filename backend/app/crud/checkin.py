from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin import CheckIn, CheckInStatus
from app.models.injury import InjuryRegion


async def create_check_in(
    db: AsyncSession,
    user_id: int,
    program_id: int,
    region: InjuryRegion,
    status: CheckInStatus,
    note: str | None,
) -> CheckIn:
    check_in = CheckIn(user_id=user_id, program_id=program_id, region=region, status=status, note=note)
    db.add(check_in)
    await db.flush()
    await db.commit()
    await db.refresh(check_in)
    return check_in


async def list_check_ins_for_program(db: AsyncSession, user_id: int, program_id: int) -> list[CheckIn]:
    result = await db.execute(
        select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.program_id == program_id).order_by(CheckIn.created_at)
    )
    return list(result.scalars().all())
