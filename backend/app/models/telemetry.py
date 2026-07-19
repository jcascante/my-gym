"""Append-only engine telemetry. No automated retention/deletion policy exists yet —
treat rows as accumulating indefinitely pending a future retention decision (plan §1.7).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import _utcnow


class EngineEvent(Base):
    """One telemetry record (match score breakdown, slot selection, or feedback action).

    Append-only: no `updated_at`, no update/delete CRUD path. See module docstring for
    the retention note.
    """

    __tablename__ = "engine_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
