import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    from app.models.user import User


class EnvironmentType(str, enum.Enum):
    COMMERCIAL_GYM = "commercial_gym"
    HOME = "home"
    BODYWEIGHT = "bodyweight"
    CROSSFIT_BOX = "crossfit_box"
    POWERLIFTING_GYM = "powerlifting_gym"
    STRENGTH_GYM = "strength_gym"
    OTHER = "other"


class TrainingEnvironment(Base):
    __tablename__ = "training_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment_type: Mapped[EnvironmentType] = mapped_column(Enum(EnvironmentType), nullable=False)
    equipment_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="environments")

    def __repr__(self) -> str:
        return f"<TrainingEnvironment(id={self.id}, user_id={self.user_id}, name={self.name})>"
