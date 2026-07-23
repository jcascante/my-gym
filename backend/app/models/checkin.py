import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.injury import InjuryRegion
from app.models.user import _utcnow


class CheckInStatus(str, enum.Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class CheckIn(Base):
    """Post-session traffic-light check-in (plan §3.4, proposal §5.3). Append-only -
    the state machine (services/program/checkin.py) derives current state from the
    full history via `WorkoutProgram.constraints`, not by mutating past rows."""

    __tablename__ = "check_ins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("workout_programs.id"), nullable=False, index=True)
    region: Mapped[InjuryRegion] = mapped_column(Enum(InjuryRegion), nullable=False)
    status: Mapped[CheckInStatus] = mapped_column(Enum(CheckInStatus), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<CheckIn(id={self.id}, user_id={self.user_id}, region={self.region}, status={self.status})>"
