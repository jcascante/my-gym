from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.schemas.logging import WorkoutSetLogOut
from app.schemas.program_api import SlotPreviewOut


class ScheduleEntryOut(BaseModel):
    """One dated session as it appears in the schedule list."""

    session_id: int
    scheduled_date: date
    week: int
    status: str
    workout_id: int
    workout_name: str
    exercise_count: int
    duration_min: int


class SessionDetailOut(ScheduleEntryOut):
    """A session with its week-resolved prescription and any logged sets."""

    program_id: int
    program_name: str
    slots: list[SlotPreviewOut]
    logged_sets: list[WorkoutSetLogOut]
    reactive_deload: bool
    deload_reason: Optional[str]
    completed_at: Optional[datetime] = None


class SessionSetLogCreate(BaseModel):
    """Append a set to a session. The session supplies the workout."""

    workout_exercise_id: int
    set_number: int = Field(ge=1)
    actual_weight: Optional[float] = None
    actual_reps: Optional[int] = None
    effort_method: Literal["rpe", "rir", "borg"] = "rpe"
    actual_rpe: Optional[float] = None

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
        if effort_method == "rir" and not (0.0 <= v <= 10.0):
            raise ValueError("RIR must be 0-10")
        if effort_method == "borg" and not (6.0 <= v <= 20.0):
            raise ValueError("Borg scale must be 6-20")
        return v
