from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserWorkoutLogCreate(BaseModel):
    """Create a new workout session log."""

    workout_id: int
    readiness: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class UserWorkoutLogOut(BaseModel):
    """Returned workout session log."""

    id: int
    user_id: int
    workout_id: int
    session_date: datetime
    readiness: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutSetLogCreate(BaseModel):
    """Append a new set log to a workout session."""

    workout_id: int
    workout_exercise_id: int
    set_number: int = Field(ge=1)
    actual_weight: Optional[float] = None
    actual_reps: Optional[int] = None
    actual_rpe: Optional[float] = Field(None, ge=1.0, le=10.0)

    @field_validator("actual_weight")
    @classmethod
    def validate_weight(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Weight must be >= 0")
        return v

    @field_validator("actual_reps")
    @classmethod
    def validate_reps(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 100):
            raise ValueError("Reps must be between 1 and 100")
        return v


class WorkoutSetLogOut(BaseModel):
    """Returned set-level performance log."""

    id: int
    user_id: int
    workout_id: int
    workout_exercise_id: int
    set_number: int
    actual_weight: Optional[float]
    actual_reps: Optional[int]
    actual_rpe: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}
