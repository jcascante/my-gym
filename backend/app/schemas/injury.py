from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import InjuryCondition, InjuryPhase, InjuryRegion, InjurySource, Provocation


class InjuryRecordCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: InjuryRegion
    condition: InjuryCondition
    phase: InjuryPhase
    provocations: list[Provocation] = []
    severity: int = Field(ge=1, le=3)
    reported_at: date
    source: InjurySource


class InjuryRecordUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: Optional[InjuryRegion] = None
    condition: Optional[InjuryCondition] = None
    phase: Optional[InjuryPhase] = None
    provocations: Optional[list[Provocation]] = None
    severity: Optional[int] = Field(default=None, ge=1, le=3)
    reported_at: Optional[date] = None
    source: Optional[InjurySource] = None


class InjuryRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region: InjuryRegion
    condition: InjuryCondition
    phase: InjuryPhase
    provocations: list[Provocation]
    severity: int
    reported_at: date
    source: InjurySource
