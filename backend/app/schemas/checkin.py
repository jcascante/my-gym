from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.checkin import CheckInStatus
from app.models.injury import InjuryRegion
from app.schemas.injury import InjuryRecordCreate
from app.schemas.program_api import Advisory


class CheckInCreate(BaseModel):
    region: InjuryRegion
    status: CheckInStatus
    note: str | None = None


class CheckInResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region: InjuryRegion
    status: CheckInStatus
    note: str | None
    created_at: datetime


class CheckInResultResponse(BaseModel):
    """Response for POST .../check-ins: the persisted row plus the state machine's
    effects (plan §3.4). `draft_injury_record` is unsaved - the user confirms it via
    the existing POST /users/me/injuries, same "draft, don't mutate without
    confirmation" principle as tasks 3.1/3.2."""

    check_in: CheckInResponse
    excluded: bool
    consult_recommended: bool
    draft_injury_record: InjuryRecordCreate | None
    advisories: list[Advisory]
