import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, User, UserProfile
from app.services.program.engine_config import get_engine_config


async def _consenting_profile(db_session: AsyncSession, user: User) -> UserProfile:
    profile = UserProfile(user_id=user.id, telemetry_consent=True)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


def _match_body(environment_id: int) -> dict:
    return {
        "environment_id": environment_id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }


@pytest.mark.asyncio
async def test_match_logs_events_when_consent_given(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, test_user, db_session
):
    await _consenting_profile(db_session, test_user)

    r = await client.post("/api/v1/programs/match", json=_match_body(user_environment.id), headers=auth_headers)
    assert r.status_code == 200
    matches = r.json()

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert len(rows) == len(matches)
    for row in rows:
        assert row.event_type == "match_score"
        assert row.user_id == test_user.id
        assert row.config_version == get_engine_config().config_version
        assert {"template_id", "slug", "fit_pct", "tier", "factors", "all_infeasible"} <= row.payload.keys()


@pytest.mark.asyncio
async def test_match_logs_nothing_without_consent(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    r = await client.post("/api/v1/programs/match", json=_match_body(user_environment.id), headers=auth_headers)
    assert r.status_code == 200

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_draft_logs_slot_selection_events_when_consent_given(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, test_user, db_session
):
    await _consenting_profile(db_session, test_user)

    body = _match_body(user_environment.id)
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201

    rows = (
        (await db_session.execute(select(EngineEvent).where(EngineEvent.event_type == "slot_selection")))
        .scalars()
        .all()
    )
    assert rows
    for row in rows:
        assert row.user_id == test_user.id
        assert row.config_version == get_engine_config().config_version
        assert {"workout_key", "order", "exercise_id", "features"} <= row.payload.keys()


@pytest.mark.asyncio
async def test_draft_logs_nothing_without_consent(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    body = _match_body(user_environment.id)
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_feedback_logs_event_when_consent_given(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, test_user, db_session
):
    await _consenting_profile(db_session, test_user)

    body = _match_body(user_environment.id)
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]
    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    program = r.json()
    pid = program["program_id"]
    we_id = program["weeks"]["1"][0]["slots"][0]["workout_exercise_id"]

    r = await client.post(
        f"/api/v1/programs/{pid}/feedback",
        json={"type": "lock", "workout_exercise_id": we_id},
        headers=auth_headers,
    )
    assert r.status_code == 200

    rows = (
        (await db_session.execute(select(EngineEvent).where(EngineEvent.event_type == "feedback_action")))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == test_user.id
    assert row.config_version == get_engine_config().config_version
    assert row.payload["workout_exercise_id"] == we_id
    assert row.payload["resulting_exercise_id"] is not None
    assert row.payload["action"]["type"] == "lock"


@pytest.mark.asyncio
async def test_feedback_logs_nothing_without_consent(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    body = _match_body(user_environment.id)
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]
    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    program = r.json()
    pid = program["program_id"]
    we_id = program["weeks"]["1"][0]["slots"][0]["workout_exercise_id"]

    r = await client.post(
        f"/api/v1/programs/{pid}/feedback",
        json={"type": "lock", "workout_exercise_id": we_id},
        headers=auth_headers,
    )
    assert r.status_code == 200

    rows = (await db_session.execute(select(EngineEvent))).scalars().all()
    assert rows == []
