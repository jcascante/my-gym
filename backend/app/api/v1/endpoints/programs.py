from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import TrainingEnvironmentNotFoundError
from app.core.database import get_db
from app.crud.training_environment import get_training_environment
from app.models import User
from app.schemas import ProgramCreationRequest

router = APIRouter(prefix="/programs", tags=["programs"])


@router.post("")
async def create_program_endpoint(
    data: ProgramCreationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    environment = await get_training_environment(db, current_user.id, data.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Program generation is not yet implemented.",
    )
