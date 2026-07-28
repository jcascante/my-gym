import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    from app.models.user import User


class InjuryRegion(str, enum.Enum):
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    CERVICAL = "cervical"
    THORACIC = "thoracic"
    LUMBAR = "lumbar"
    HIP = "hip"
    KNEE = "knee"
    ANKLE_FOOT = "ankle_foot"


class InjuryCondition(str, enum.Enum):
    ACUTE_PAIN = "acute_pain"
    POST_SURGICAL = "post_surgical"
    TENDINOPATHY = "tendinopathy"
    JOINT_INSTABILITY = "joint_instability"
    CHRONIC_RECURRENT = "chronic_recurrent"
    RESOLVED_CAUTIOUS = "resolved_cautious"
    UNSPECIFIED = "unspecified"


class InjuryPhase(str, enum.Enum):
    ACUTE = "acute"
    REHABILITATING = "rehabilitating"
    RESOLVED_CAUTIOUS = "resolved_cautious"
    CLEARED = "cleared"


class InjurySource(str, enum.Enum):
    USER_REPORTED = "user_reported"
    PROFESSIONAL_CLEARED = "professional_cleared"


class InjuryRecord(Base):
    __tablename__ = "injury_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    region: Mapped[InjuryRegion] = mapped_column(Enum(InjuryRegion), nullable=False)
    condition: Mapped[InjuryCondition] = mapped_column(Enum(InjuryCondition), nullable=False)
    phase: Mapped[InjuryPhase] = mapped_column(Enum(InjuryPhase), nullable=False)
    provocations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    reported_at: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[InjurySource] = mapped_column(Enum(InjurySource), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="injury_records")

    def __repr__(self) -> str:
        return f"<InjuryRecord(id={self.id}, user_id={self.user_id}, region={self.region})>"
