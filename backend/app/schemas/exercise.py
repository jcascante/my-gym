from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BodyRegion, Contraindication, Equipment, ExperienceLevel, MovementPattern, Muscle, Provocation


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    movement_slug: str
    body_region: BodyRegion
    movement_pattern: MovementPattern
    primary_muscles: list[Muscle]
    secondary_muscles: list[Muscle]
    equipment_tags: list[Equipment]
    difficulty_level: ExperienceLevel
    instructions: str
    form_cues: list[str]
    safety_notes: str | None
    contraindications: list[Contraindication]
    provocation_tags: list[Provocation]
    is_unilateral: bool
    is_compound: bool
    created_at: datetime
    updated_at: datetime
