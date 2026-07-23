from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


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
    effort_method: Literal["rpe", "rir", "borg"] = "rpe"
    actual_rpe: Optional[float] = Field(None, description="Actual effort value")

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

    @field_validator("actual_rpe")
    @classmethod
    def validate_effort_value(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        if v is None:
            return v
        effort_method = info.data.get("effort_method", "rpe")
        if effort_method == "rpe" and not (1.0 <= v <= 10.0):
            raise ValueError("RPE must be 1-10")
        elif effort_method == "rir" and not (0.0 <= v <= 10.0):
            raise ValueError("RIR must be 0-10")
        elif effort_method == "borg" and not (6.0 <= v <= 20.0):
            raise ValueError("Borg scale must be 6-20")
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
    effort_method: str
    created_at: datetime

    model_config = {"from_attributes": True}
