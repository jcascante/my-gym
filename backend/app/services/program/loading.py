from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ProgramNotFoundError
from app.crud.program import get_program, get_template
from app.models.program import WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.style_override import apply_progression_style


async def load_program_with_definition(
    db: AsyncSession, user_id: int, program_id: int
) -> tuple[WorkoutProgram, TemplateDefinition]:
    program = await get_program(db, user_id, program_id)
    if program is None:
        raise ProgramNotFoundError()
    template = await get_template(db, program.template_id)
    definition = TemplateDefinition.from_orm_template(template)
    style = program.constraints.get("progression_style", "consistent")
    return program, apply_progression_style(definition, style)
