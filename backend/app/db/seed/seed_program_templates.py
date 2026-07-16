import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.db.seed.program_templates import PROGRAM_TEMPLATE_SEED
from app.models import ProgramTemplate


async def seed_program_templates(db: AsyncSession) -> None:
    for entry in PROGRAM_TEMPLATE_SEED:
        existing = (
            await db.execute(select(ProgramTemplate).where(ProgramTemplate.slug == entry["slug"]))
        ).scalar_one_or_none()
        if existing is None:
            db.add(ProgramTemplate(**entry))
        else:
            for key, value in entry.items():
                setattr(existing, key, value)
            db.add(existing)
    await db.commit()


async def main() -> None:
    async with async_session() as session:
        await seed_program_templates(session)
        print("Program template seed data upserted successfully")


if __name__ == "__main__":
    asyncio.run(main())
