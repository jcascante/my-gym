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


@pytest.mark.asyncio
async def test_seed_sets_duration_weeks_range_per_template(db_session):
    await seed_program_templates(db_session)
    rows = (await db_session.execute(select(ProgramTemplate))).scalars().all()
    by_slug = {r.slug: r for r in rows}

    full_body = by_slug["full-body-x3"]
    assert (full_body.duration_weeks_min, full_body.duration_weeks_default, full_body.duration_weeks_max) == (
        4,
        8,
        12,
    )

    ppl = by_slug["push-pull-legs-x6"]
    assert (ppl.duration_weeks_min, ppl.duration_weeks_default, ppl.duration_weeks_max) == (6, 12, 18)

    for r in rows:
        assert r.duration_weeks_min <= r.duration_weeks_default <= r.duration_weeks_max
