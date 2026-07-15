from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import ALLOWED_EQUIPMENT_TAGS
from app.models import EnvironmentType


def _validate_equipment_tags(tags: list[str]) -> list[str]:
    unknown = sorted(set(tags) - set(ALLOWED_EQUIPMENT_TAGS))
    if unknown:
        raise ValueError(f"Unknown equipment tags: {', '.join(unknown)}")
    return tags


class TrainingEnvironmentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    environment_type: EnvironmentType
    equipment_tags: list[str] = []
    is_default: bool = False

    @field_validator("equipment_tags")
    @classmethod
    def validate_equipment_tags(cls, tags: list[str]) -> list[str]:
        return _validate_equipment_tags(tags)


class TrainingEnvironmentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    environment_type: Optional[EnvironmentType] = None
    equipment_tags: Optional[list[str]] = None
    is_default: Optional[bool] = None

    @field_validator("equipment_tags")
    @classmethod
    def validate_equipment_tags(cls, tags: Optional[list[str]]) -> Optional[list[str]]:
        if tags is None:
            return tags
        return _validate_equipment_tags(tags)


class TrainingEnvironmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    environment_type: EnvironmentType
    equipment_tags: list[str]
    is_default: bool
