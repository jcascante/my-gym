from pydantic import BaseModel
from typing import Optional


class UserProfileRequest(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[str] = None
    fitness_focus: Optional[str] = None
    experience_level: Optional[str] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
    equipment: Optional[str] = None
    injuries_limitations: Optional[str] = None
    short_term_goals: Optional[str] = None
    medium_term_goals: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: Optional[str] = None
    fitness_focus: Optional[str] = None
    experience_level: Optional[str] = None
    days_per_week: Optional[int] = None
    workout_duration_min: Optional[int] = None
    equipment: Optional[str] = None
    injuries_limitations: Optional[str] = None
    short_term_goals: Optional[str] = None
    medium_term_goals: Optional[str] = None

    class Config:
        from_attributes = True


class UserWithProfileResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True
