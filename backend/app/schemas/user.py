from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import ActivityLevel, ExperienceLevel, FitnessFocus


class UserProfileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    fitness_focus: Optional[FitnessFocus] = None
    goal_weights: Optional[dict[str, float]] = None
    experience_level: Optional[ExperienceLevel] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
    injuries_limitations: Optional[str] = None
    short_term_goals: Optional[str] = None
    medium_term_goals: Optional[str] = None

    @field_validator("goal_weights")
    @classmethod
    def _validate_goal_weights_range(cls, v: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if v is None:
            return v
        for goal, weight in v.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"goal_weights weight for '{goal}' must be in [0.0, 1.0], got {weight}")
        return v


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    fitness_focus: Optional[FitnessFocus] = None
    goal_weights: Optional[dict[str, float]] = None
    experience_level: Optional[ExperienceLevel] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
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
