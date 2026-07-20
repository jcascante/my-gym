import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.training_environment import TrainingEnvironment


def _utcnow() -> datetime:
    # Columns are `DateTime` (no timezone), so keep the stored value naive
    # UTC rather than switching the on-disk representation.
    return datetime.now(UTC).replace(tzinfo=None)


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"


class FitnessFocus(str, enum.Enum):
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    FLEXIBILITY = "flexibility"
    GENERAL = "general"


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    environments: Mapped[list["TrainingEnvironment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(20))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[ActivityLevel | None] = mapped_column(Enum(ActivityLevel))
    fitness_focus: Mapped[FitnessFocus | None] = mapped_column(Enum(FitnessFocus))
    goal_weights: Mapped[dict[str, float] | None] = mapped_column(JSON)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(Enum(ExperienceLevel))
    days_per_week: Mapped[int | None] = mapped_column(Integer)
    workout_duration_min: Mapped[int | None] = mapped_column(Integer)
    injuries_limitations: Mapped[str | None] = mapped_column(Text)
    short_term_goals: Mapped[str | None] = mapped_column(Text)
    medium_term_goals: Mapped[str | None] = mapped_column(Text)
    telemetry_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, focus={self.fitness_focus})>"
