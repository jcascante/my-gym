import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    pass


class ProgramStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProgramTemplate(Base):
    __tablename__ = "program_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    goals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    experience_levels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    days_per_week_min: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week_max: Mapped[int] = mapped_column(Integer, nullable=False)
    session_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    session_duration_max: Mapped[int] = mapped_column(Integer, nullable=False)
    split: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    progression_ref: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    required_inputs: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class WorkoutProgram(Base):
    __tablename__ = "workout_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("program_templates.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("training_environments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[ProgramStatus] = mapped_column(Enum(ProgramStatus), nullable=False, default=ProgramStatus.DRAFT)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    weight_unit: Mapped[str] = mapped_column(String(3), nullable=False, default="kg")
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="Workout.order",
    )


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("workout_programs.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    program: Mapped["WorkoutProgram"] = relationship(back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    fills_rule: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_min: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_max: Mapped[int] = mapped_column(Integer, nullable=False)
    base_load: Mapped[float | None] = mapped_column(Float)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    scheme_key: Mapped[str] = mapped_column(String(50), nullable=False)
    target_rpe: Mapped[float | None] = mapped_column(Float)
    intensity_pct: Mapped[float | None] = mapped_column(Float)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_user_swapped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rotation_pool: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
