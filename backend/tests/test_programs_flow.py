import pytest

from app.core import hash_password
from app.crud.program import get_program
from app.crud.training_environment import create_training_environment
from app.models import User
from app.services.program.engine_config import get_engine_config


@pytest.mark.asyncio
async def test_full_flow(client, auth_headers, seeded_templates, seeded_exercises, user_environment):
    # 1. match
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    assert r.status_code == 200
    matches = r.json()
    assert matches and "fit_pct" in matches[0]

    # 2. draft
    draft_body = {**body, "template_id": matches[0]["template_id"], "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201
    program = r.json()
    pid = program["program_id"]
    assert program["status"] == "draft"
    assert 1 in {int(k) for k in program["weeks"].keys()}

    # 3. feedback: lock first slot
    we_id = program["weeks"]["1"][0]["slots"][0]["workout_exercise_id"]
    r = await client.post(
        f"/api/v1/programs/{pid}/feedback", json={"type": "lock", "workout_exercise_id": we_id}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["weeks"]["1"][0]["slots"][0]["is_locked"] is True

    # 4. accept
    r = await client.post(f"/api/v1/programs/{pid}/accept", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_draft_stores_engine_config_version_in_constraints(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, test_user, db_session
):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201
    program_id = r.json()["program_id"]

    saved = await get_program(db_session, test_user.id, program_id)
    assert saved is not None
    assert saved.constraints["engine_config_version"] == get_engine_config().config_version


@pytest.mark.asyncio
async def test_draft_malformed_required_inputs_returns_422(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment
):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()[0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": "not-a-number"}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_match_unauthorized(client, user_environment):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_match_404_missing_environment(client, auth_headers):
    body = {
        "environment_id": 9999,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_match_404_foreign_environment(client, auth_headers, db_session):
    other_user = User(
        email="other-program@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    other_environment = await create_training_environment(
        db_session, other_user.id, {"name": "Other's Gym", "environment_type": "home", "equipment_tags": []}
    )

    body = {
        "environment_id": other_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_match_422_malformed_payload(client, auth_headers, user_environment):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "weight_unit": "kg",
        "duration_weeks": 8,
        # fitness_focus omitted
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_match_returns_new_factor_keys(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    resp = await authenticated_client.post(
        "/api/v1/programs/match",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "strength",
            "movement_preferences": {"kettlebell": 1.5},
            "complementary_focus": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert "movement_preference" in body[0]["factors"]
    assert "focus_complement" in body[0]["factors"]
    assert "periodization" in body[0]["factors"]
