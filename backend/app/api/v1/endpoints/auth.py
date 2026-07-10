from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import InvalidTokenError, get_logger, settings
from app.core.database import get_db
from app.models import User
from app.schemas import LoginRequest, SignupRequest, UserResponse
from app.services.auth import create_tokens, login, signup, verify_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

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
    logger.info(f"Signup attempt for email: {request.email}")
    user = await signup(db, request.email, request.password, request.first_name, request.last_name)
    logger.info(f"User signed up successfully: {user.id} ({request.email})")
    return user


@router.post("/login", response_model=UserResponse)
async def login_endpoint(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    logger.info(f"Login attempt for email: {request.email}")
    user = await login(db, request.email, request.password)
    logger.info(f"User logged in successfully: {user.id} ({request.email})")
    tokens = create_tokens(user.id)
    _set_auth_cookies(response, tokens)
    return user


@router.post("/refresh", status_code=200)
async def refresh_endpoint(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> dict[str, str]:
    if not refresh_token:
        logger.warning("Token refresh attempted without refresh_token cookie")
        raise InvalidTokenError("No refresh token provided")

    payload = await verify_refresh_token(refresh_token)
    user_id = payload["user_id"]
    tokens = create_tokens(user_id)
    logger.info(f"Token refreshed for user: {user_id}")
    _set_auth_cookies(response, tokens)
    return {"message": "Token refreshed"}


@router.post("/logout", status_code=200)
async def logout_endpoint(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    logger.info(f"User logged out: {current_user.id}")
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
