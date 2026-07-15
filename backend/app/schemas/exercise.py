from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BodyRegion, ExperienceLevel, MovementPattern


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    movement_slug: str
    body_region: BodyRegion
    movement_pattern: MovementPattern
    primary_muscles: list[str]
    secondary_muscles: list[str]
    equipment_tags: list[str]
    difficulty_level: ExperienceLevel
    instructions: str
    form_cues: list[str]
    safety_notes: str | None
    contraindications: list[str]
    created_at: datetime
    updated_at: datetime
