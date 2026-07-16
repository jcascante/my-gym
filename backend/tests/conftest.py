import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import hash_password
from app.core.database import Base, get_db
from app.crud.training_environment import create_training_environment
from app.db.seed.seed_exercises import upsert_exercises
from app.db.seed.seed_program_templates import seed_program_templates
from app.main import app
from app.models import Exercise, ProgramTemplate, TrainingEnvironment, User
from app.services.auth import create_tokens


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_local = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_local() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        first_name="Test",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_token(test_user: User) -> str:
    tokens = create_tokens(test_user.id)
    return tokens["access_token"]


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, test_user_token: str) -> AsyncClient:
    client.cookies.set("access_token", test_user_token)
    return client


@pytest.fixture
def db(db_session: AsyncSession) -> AsyncSession:
    return db_session


@pytest_asyncio.fixture
async def sample_template_orm(db_session: AsyncSession) -> ProgramTemplate:
    """The seeded full-body-x3 ProgramTemplate row, with a real DB-assigned id."""
    await seed_program_templates(db_session)
    result = await db_session.execute(select(ProgramTemplate).where(ProgramTemplate.slug == "full-body-x3"))
    return result.scalar_one()


@pytest_asyncio.fixture
async def sample_exercises(db_session: AsyncSession) -> list[Exercise]:
    """The full seeded exercise library, with real DB-assigned ids."""
    await upsert_exercises(db_session)
    result = await db_session.execute(select(Exercise).where(Exercise.is_active.is_(True)))
    return list(result.scalars().all())


@pytest.fixture
def auth_headers(test_user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest_asyncio.fixture
async def seeded_templates(db_session: AsyncSession) -> None:
    await seed_program_templates(db_session)


@pytest_asyncio.fixture
async def seeded_exercises(db_session: AsyncSession) -> list[Exercise]:
    await upsert_exercises(db_session)
    result = await db_session.execute(select(Exercise).where(Exercise.is_active.is_(True)))
    return list(result.scalars().all())


@pytest_asyncio.fixture
async def user_environment(db_session: AsyncSession, test_user: User) -> TrainingEnvironment:
    return await create_training_environment(
        db_session,
        test_user.id,
        {
            "name": "Test Gym",
            "environment_type": "commercial_gym",
            "equipment_tags": [
                "barbell",
                "squat_rack",
                "bench",
                "dumbbells",
                "pull_up_bar",
                "cable_machine",
                "resistance_bands",
                "none",
            ],
        },
    )
