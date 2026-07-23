"""Telemetry recording helper (plan §1.7, minimal).

`record_event` commits itself rather than piggybacking on the caller's own commit — it
is used from `/match`, which otherwise never persists anything, as well as `/draft` and
`/feedback`, which commit separately for their own writes. One extra commit per event is
an accepted cost for this minimal version; commits are not batched/deferred across
endpoints.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, User


async def record_event(
    db: AsyncSession,
    *,
    user: User,
    event_type: str,
    payload: dict[str, Any],
    config_version: str,
) -> None:
    if user.profile is None or not user.profile.telemetry_consent:
        return
    db.add(
        EngineEvent(
            user_id=user.id,
            event_type=event_type,
            payload=payload,
            config_version=config_version,
        )
    )
    await db.commit()
