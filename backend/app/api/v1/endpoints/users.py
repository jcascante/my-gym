from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.crud.user import create_or_update_user_profile
from app.models import User
from app.schemas import UserProfileRequest, UserWithProfileResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserWithProfileResponse)
async def get_current_user_endpoint(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/profile", response_model=UserWithProfileResponse)
async def create_update_profile_endpoint(
    profile_data: UserProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    filtered_data = {
        k: v for k, v in profile_data.model_dump().items() if v is not None
    }
    await create_or_update_user_profile(db, current_user.id, filtered_data)
    await db.refresh(current_user)
    return current_user
