import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, User, UserProfile


@pytest.mark.asyncio
async def test_engine_event_persists_with_all_fields(db_session: AsyncSession, test_user: User):
    event = EngineEvent(
        user_id=test_user.id,
        event_type="match_score",
        payload={"template_id": 1, "fit_pct": 80},
        config_version="v1",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.id is not None
    assert event.created_at is not None

    found = (await db_session.execute(select(EngineEvent))).scalar_one()
    assert found.user_id == test_user.id
    assert found.event_type == "match_score"
    assert found.payload == {"template_id": 1, "fit_pct": 80}
    assert found.config_version == "v1"


@pytest.mark.asyncio
async def test_engine_event_has_no_updated_at_column():
    assert not hasattr(EngineEvent, "updated_at")


@pytest.mark.asyncio
async def test_user_profile_telemetry_consent_defaults_to_false(db_session: AsyncSession, test_user: User):
    profile = UserProfile(user_id=test_user.id)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.telemetry_consent is False


@pytest.mark.asyncio
async def test_user_profile_telemetry_consent_can_be_set_true(db_session: AsyncSession, test_user: User):
    profile = UserProfile(user_id=test_user.id, telemetry_consent=True)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.telemetry_consent is True
