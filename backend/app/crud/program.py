from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ProgramTemplate, Workout, WorkoutProgram


async def list_active_templates(db: AsyncSession) -> list[ProgramTemplate]:
    result = await db.execute(select(ProgramTemplate).where(ProgramTemplate.is_active.is_(True)))
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: int) -> ProgramTemplate | None:
    result = await db.execute(select(ProgramTemplate).where(ProgramTemplate.id == template_id))
    return result.scalar_one_or_none()


async def get_program(db: AsyncSession, user_id: int, program_id: int) -> WorkoutProgram | None:
    result = await db.execute(
        select(WorkoutProgram)
        .where(WorkoutProgram.id == program_id, WorkoutProgram.user_id == user_id)
        .options(selectinload(WorkoutProgram.workouts).selectinload(Workout.exercises))
    )
    return result.scalar_one_or_none()


async def save_program(db: AsyncSession, program: WorkoutProgram) -> WorkoutProgram:
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program
