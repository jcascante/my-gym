from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import InvalidCredentialsError, UserAlreadyExistsError, settings
from app.core.database import get_db
from app.models import User
from app.schemas import LoginRequest, SignupRequest, UserResponse
from app.services.auth import create_tokens, login, signup, verify_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_auth_cookies(response: Response, tokens: dict[str, str]) -> None:
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path=REFRESH_COOKIE_PATH)


@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup_endpoint(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user = await signup(db, request.email, request.password, request.first_name, request.last_name)
        return user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/login", response_model=UserResponse)
async def login_endpoint(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user = await login(db, request.email, request.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=e.message)

    tokens = create_tokens(user.id)
    _set_auth_cookies(response, tokens)
    return user


@router.post("/refresh", status_code=200)
async def refresh_endpoint(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> dict[str, str]:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = await verify_refresh_token(refresh_token)
    tokens = create_tokens(payload["user_id"])
    _set_auth_cookies(response, tokens)
    return {"message": "Token refreshed"}


@router.post("/logout", status_code=200)
async def logout_endpoint(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
