import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import ExperienceLevel, _utcnow

if TYPE_CHECKING:
    pass


class BodyRegion(str, enum.Enum):
    UPPER_BODY = "upper_body"
    LOWER_BODY = "lower_body"
    CORE = "core"
    FULL_BODY = "full_body"


class MovementPattern(str, enum.Enum):
    SQUAT = "squat"
    HINGE = "hinge"
    LUNGE = "lunge"
    HORIZONTAL_PUSH = "horizontal_push"
    VERTICAL_PUSH = "vertical_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PULL = "vertical_pull"
    ROTATION = "rotation"
    ANTI_ROTATION = "anti_rotation"
    CARRY = "carry"
    ISOLATION = "isolation"
    LOCOMOTION = "locomotion"
    MOBILITY = "mobility"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    movement_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body_region: Mapped[BodyRegion] = mapped_column(Enum(BodyRegion), nullable=False)
    movement_pattern: Mapped[MovementPattern] = mapped_column(Enum(MovementPattern), nullable=False)
    primary_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    secondary_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    equipment_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    difficulty_level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    form_cues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contraindications: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, name={self.name}, slug={self.slug})>"
