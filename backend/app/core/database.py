from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
