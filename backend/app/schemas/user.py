from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import ActivityLevel, Equipment, ExperienceLevel, FitnessFocus


class UserProfileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    fitness_focus: Optional[FitnessFocus] = None
    experience_level: Optional[ExperienceLevel] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
    equipment: Optional[Equipment] = None
    injuries_limitations: Optional[str] = None
    short_term_goals: Optional[str] = None
    medium_term_goals: Optional[str] = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    fitness_focus: Optional[FitnessFocus] = None
    experience_level: Optional[ExperienceLevel] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
    equipment: Optional[Equipment] = None
    injuries_limitations: Optional[str] = None
    short_term_goals: Optional[str] = None
    medium_term_goals: Optional[str] = None


class UserWithProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    profile: Optional[UserProfileResponse] = None
