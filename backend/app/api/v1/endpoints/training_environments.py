from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import TrainingEnvironmentNotFoundError
from app.core.database import get_db
from app.crud.training_environment import (
    create_training_environment,
    delete_training_environment,
    get_training_environment,
    list_training_environments,
    update_training_environment,
)
from app.models import TrainingEnvironment, User
from app.schemas import (
    TrainingEnvironmentCreate,
    TrainingEnvironmentResponse,
    TrainingEnvironmentUpdate,
)

router = APIRouter(prefix="/training-environments", tags=["training-environments"])


async def _get_owned_environment(db: AsyncSession, current_user: User, environment_id: int) -> TrainingEnvironment:
    environment = await get_training_environment(db, current_user.id, environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    return environment


@router.get("", response_model=list[TrainingEnvironmentResponse])
async def list_training_environments_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrainingEnvironment]:
    return await list_training_environments(db, current_user.id)


@router.post("", response_model=TrainingEnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_training_environment_endpoint(
    data: TrainingEnvironmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingEnvironment:
    return await create_training_environment(db, current_user.id, data.model_dump())


@router.get("/{environment_id}", response_model=TrainingEnvironmentResponse)
async def get_training_environment_endpoint(
    environment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingEnvironment:
    return await _get_owned_environment(db, current_user, environment_id)


@router.patch("/{environment_id}", response_model=TrainingEnvironmentResponse)
async def update_training_environment_endpoint(
    environment_id: int,
    data: TrainingEnvironmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingEnvironment:
    environment = await _get_owned_environment(db, current_user, environment_id)
    return await update_training_environment(db, environment, data.model_dump(exclude_unset=True))


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_environment_endpoint(
    environment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    environment = await _get_owned_environment(db, current_user, environment_id)
    await delete_training_environment(db, environment)
