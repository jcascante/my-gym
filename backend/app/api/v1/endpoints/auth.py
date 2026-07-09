from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import UserAlreadyExistsError, InvalidCredentialsError
from app.core.database import get_db
from app.models import User
from app.schemas import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from app.services.auth import signup, login, create_tokens, verify_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user = await login(db, request.email, request.password)
        tokens = create_tokens(user.id)
        return TokenResponse(**tokens)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=e.message)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(request: RefreshTokenRequest) -> TokenResponse:
    payload = await verify_refresh_token(request.refresh_token)
    user_id = payload["user_id"]
    tokens = create_tokens(user_id)
    return TokenResponse(**tokens)


@router.post("/logout", status_code=200)
async def logout_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}
