from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.models import User, UserProfile


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    from sqlalchemy.orm import selectinload

    result = await db.execute(select(User).options(selectinload(User.profile)).where(User.id == user_id))
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


async def get_user_profile(db: AsyncSession, user_id: int) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def create_or_update_user_profile(
    db: AsyncSession,
    user_id: int,
    profile_data: dict[str, Any],
) -> UserProfile:
    existing_profile = await get_user_profile(db, user_id)

    if existing_profile:
        for key, value in profile_data.items():
            if value is not None:
                setattr(existing_profile, key, value)
        db.add(existing_profile)
    else:
        existing_profile = UserProfile(user_id=user_id, **profile_data)
        db.add(existing_profile)

    await db.flush()
    await db.commit()
    await db.refresh(existing_profile)
    return existing_profile
