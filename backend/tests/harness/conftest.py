"""Session-scoped fixtures for the A/B harness.

The real seeded catalog (148 exercises, 4 templates) is the same static data for every
synthetic profile, so it's loaded into an in-memory SQLite DB exactly once per test
session -- reloading it per profile would dominate latency measurements with
fixture/DB overhead that has nothing to do with the engine itself (task brief, ground
truth section). This mirrors `tests/conftest.py`'s `seeded_templates`/`seeded_exercises`
fixture pattern, but at session scope and via a synchronous `asyncio.run()` wrapper
(pytest-asyncio's default fixtures are function-scoped) so it only runs once.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.db.seed.seed_exercises import upsert_exercises
from app.db.seed.seed_program_templates import seed_program_templates
from app.models import Exercise, ProgramTemplate
from tests.harness.profiles import SyntheticProfile, bounded_profiles
from tests.harness.runner import ProfileResult, build_definitions, run_profile


async def _load_catalog() -> tuple[list[ProgramTemplate], list[Exercise]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_local = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_local() as session:
        await seed_program_templates(session)
        await upsert_exercises(session)
        templates = list(
            (await session.execute(select(ProgramTemplate).where(ProgramTemplate.is_active.is_(True)))).scalars().all()
        )
        exercises = list((await session.execute(select(Exercise).where(Exercise.is_active.is_(True)))).scalars().all())
        # Detach so the ORM objects remain usable after the session/engine close below.
        # Both models are plain columns with no relationships, so this is safe.
        session.expunge_all()

    await engine.dispose()
    return templates, exercises


@pytest.fixture(scope="session")
def catalog() -> tuple[list[ProgramTemplate], list[Exercise]]:
    return asyncio.run(_load_catalog())


@pytest.fixture(scope="session")
def catalog_templates(catalog: tuple[list[ProgramTemplate], list[Exercise]]) -> list[ProgramTemplate]:
    return catalog[0]


@pytest.fixture(scope="session")
def catalog_exercises(catalog: tuple[list[ProgramTemplate], list[Exercise]]) -> list[Exercise]:
    return catalog[1]


@pytest.fixture(scope="session")
def bounded_grid() -> list[SyntheticProfile]:
    return bounded_profiles()


@pytest.fixture(scope="session")
def grid_results(
    catalog_templates: list[ProgramTemplate],
    catalog_exercises: list[Exercise],
    bounded_grid: list[SyntheticProfile],
) -> list[ProfileResult]:
    """`run_profile` (old + new formula) over the full bounded grid, computed once and
    shared by the report/rank-agreement/advisory-rate/latency tests."""
    definitions = build_definitions(catalog_templates)
    return [run_profile(profile, catalog_templates, catalog_exercises, definitions) for profile in bounded_grid]
