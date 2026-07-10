import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import hash_password
from app.core.database import Base, get_db
from app.main import app
from app.models import User
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
