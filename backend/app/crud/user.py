from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, first_name: str, last_name: str) -> User:
    hashed_password = hash_password(password)
    user = User(
        email=email,
        password_hash=hashed_password,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user
