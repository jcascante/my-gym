from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import InjuryRecordNotFoundError
from app.core.database import get_db
from app.crud.injury import (
    create_injury_record,
    delete_injury_record,
    get_injury_record,
    list_injury_records,
    update_injury_record,
)
from app.models import InjuryRecord, User
from app.schemas import InjuryRecordCreate, InjuryRecordResponse, InjuryRecordUpdate

router = APIRouter(prefix="/users/me/injuries", tags=["injuries"])


async def _get_owned_injury_record(db: AsyncSession, current_user: User, injury_id: int) -> InjuryRecord:
    injury_record = await get_injury_record(db, current_user.id, injury_id)
    if injury_record is None:
        raise InjuryRecordNotFoundError()
    return injury_record


@router.get("", response_model=list[InjuryRecordResponse])
async def list_injury_records_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InjuryRecord]:
    return await list_injury_records(db, current_user.id)


@router.post("", response_model=InjuryRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_injury_record_endpoint(
    data: InjuryRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InjuryRecord:
    return await create_injury_record(db, current_user.id, data.model_dump())


@router.get("/{injury_id}", response_model=InjuryRecordResponse)
async def get_injury_record_endpoint(
    injury_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InjuryRecord:
    return await _get_owned_injury_record(db, current_user, injury_id)


@router.patch("/{injury_id}", response_model=InjuryRecordResponse)
async def update_injury_record_endpoint(
    injury_id: int,
    data: InjuryRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InjuryRecord:
    injury_record = await _get_owned_injury_record(db, current_user, injury_id)
    return await update_injury_record(db, injury_record, data.model_dump(exclude_unset=True))


@router.delete("/{injury_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_injury_record_endpoint(
    injury_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    injury_record = await _get_owned_injury_record(db, current_user, injury_id)
    await delete_injury_record(db, injury_record)
