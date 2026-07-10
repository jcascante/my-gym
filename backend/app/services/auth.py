import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.crud.user import create_user, get_user_by_email
from app.models import User


async def signup(db: AsyncSession, email: str, password: str, first_name: str, last_name: str) -> User:
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise UserAlreadyExistsError(f"User with email {email} already exists")

    user = await create_user(db, email, password, first_name, last_name)
    return user


async def login(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if not user:
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    return user


async def verify_refresh_token(token: str) -> dict[str, int]:
    try:
        payload = decode_token(token, expected_type="refresh")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(str(e)) from e

    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError()
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        raise InvalidTokenError("Invalid token subject") from e
    return {"user_id": user_id}


def create_tokens(user_id: int) -> dict[str, str]:
    access_token = create_access_token(data={"sub": str(user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user_id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
