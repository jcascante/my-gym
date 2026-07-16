import pytest
from sqlalchemy import select

from app.db.seed.seed_program_templates import seed_program_templates
from app.models import ProgramTemplate
from app.schemas.template import TemplateDefinition


@pytest.mark.asyncio
async def test_seed_inserts_and_is_idempotent(db_session):
    await seed_program_templates(db_session)
    await seed_program_templates(db_session)  # second run must not duplicate
    rows = (await db_session.execute(select(ProgramTemplate))).scalars().all()
    slugs = {r.slug for r in rows}
    assert {"full-body-x3", "upper-lower-x4", "push-pull-legs-x6", "bodyweight-full-body-x3"} <= slugs
    for r in rows:
        TemplateDefinition.from_orm_template(r)  # every seed parses cleanly
