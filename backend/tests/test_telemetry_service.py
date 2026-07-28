import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, User, UserProfile
from app.services.program.telemetry import record_event


@pytest.mark.asyncio
async def test_record_event_persists_row_when_consent_given(db_session: AsyncSession, test_user: User):
    profile = UserProfile(user_id=test_user.id, telemetry_consent=True)
    db_session.add(profile)
    await db_session.commit()
    test_user.profile = profile

    await record_event(
        db_session,
        user=test_user,
        event_type="match_score",
        payload={"template_id": 1, "fit_pct": 90},
        config_version="v1",
    )

    found = (await db_session.execute(select(EngineEvent))).scalar_one()
    assert found.user_id == test_user.id
    assert found.event_type == "match_score"
    assert found.payload == {"template_id": 1, "fit_pct": 90}
    assert found.config_version == "v1"


@pytest.mark.asyncio
async def test_record_event_noop_when_consent_false(db_session: AsyncSession, test_user: User):
    profile = UserProfile(user_id=test_user.id, telemetry_consent=False)
    db_session.add(profile)
    await db_session.commit()
    test_user.profile = profile

    await record_event(
        db_session,
        user=test_user,
        event_type="match_score",
        payload={"template_id": 1},
        config_version="v1",
    )

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_record_event_noop_when_no_profile(db_session: AsyncSession, test_user: User):
    test_user.profile = None

    await record_event(
        db_session,
        user=test_user,
        event_type="match_score",
        payload={"template_id": 1},
        config_version="v1",
    )

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert rows == []
