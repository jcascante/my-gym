from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    pass


class UserWorkoutLog(Base):
    """
    Immutable session-level workout log.
    Created once per workout session start; tracks readiness + completion notes.
    """

    __tablename__ = "user_workout_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), nullable=False, index=True)
    session_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    readiness: Mapped[int | None] = mapped_column(Integer)  # 1-5 scale, nullable if not provided
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class WorkoutSetLog(Base):
    """
    Immutable per-set performance log.
    Appended during/after each completed set; tracks actual weight, reps, RPE.
    A correction is a second row for the same set, not an update - readers
    (get_set_logs, get_set_logs_for_sessions, get_set_logs_for_session) dedupe to
    the highest id per (session_id, workout_exercise_id, set_number).
    """

    __tablename__ = "workout_set_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    workout_exercise_id: Mapped[int] = mapped_column(ForeignKey("workout_exercises.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), nullable=False, index=True)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_weight: Mapped[float | None] = mapped_column(Float)
    actual_reps: Mapped[int | None] = mapped_column(Integer)
    actual_rpe: Mapped[float | None] = mapped_column(Float)  # range depends on effort_method
    effort_method: Mapped[str] = mapped_column(String(20), default="rpe", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
