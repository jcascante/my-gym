from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserWorkoutLogCreate(BaseModel):
    """Create a new workout session log."""

    readiness: Optional[int] = Field(None, ge=1, le=5)
    phase: Optional[str] = Field(None, description="'pre' or 'post'")
    notes: Optional[str] = None


class UserWorkoutLogOut(BaseModel):
    """Returned workout session log."""

    id: int
    user_id: int
    workout_id: int
    session_id: int
    session_date: datetime
    readiness: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutSetLogOut(BaseModel):
    """Returned set-level performance log."""

    id: int
    user_id: int
    workout_id: int
    session_id: int
    workout_exercise_id: int
    set_number: int
    actual_weight: Optional[float]
    actual_reps: Optional[int]
    actual_rpe: Optional[float]
    effort_method: str
    created_at: datetime

    model_config = {"from_attributes": True}
