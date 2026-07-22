import json

import pytest
from sqlalchemy import text

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
    data = r.json()
    matches = data["matches"]
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
async def test_exclude_persists_to_db_not_just_in_memory_response(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    """Regression: apply_feedback mutated program.constraints in place before
    reassigning it, so the reassignment was a same-content no-op that SQLAlchemy's
    JSON change-tracking silently dropped - the response and in-memory object looked
    right, but excluded_exercise_ids never reached the database. Query raw SQL,
    bypassing the session's identity map, so a masked write can't fake a pass."""
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()["matches"][0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    program = r.json()
    pid = program["program_id"]
    slot = program["weeks"]["1"][0]["slots"][0]
    we_id = slot["workout_exercise_id"]
    original_exercise_id = slot["exercise_id"]

    r = await client.post(
        f"/api/v1/programs/{pid}/feedback",
        json={"type": "exclude", "workout_exercise_id": we_id},
        headers=auth_headers,
    )
    assert r.status_code == 200

    row = await db_session.execute(text("SELECT constraints FROM workout_programs WHERE id = :pid"), {"pid": pid})
    persisted_constraints = json.loads(row.scalar_one())
    assert original_exercise_id in persisted_constraints["excluded_exercise_ids"]


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
    template_id = r.json()["matches"][0]["template_id"]

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
    template_id = r.json()["matches"][0]["template_id"]

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
    assert body["matches"]
    assert "movement_preference" in body["matches"][0]["factors"]
    assert "focus_complement" in body["matches"][0]["factors"]
    assert "periodization" in body["matches"][0]["factors"]


@pytest.mark.asyncio
async def test_match_uses_profile_goal_weights_to_score_templates(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    """profile.goal_weights must actually reach rank_templates via MatchInput.goal_vector.

    "bodyweight-full-body-x3" has goals=["general"] (see app/db/seed/program_templates.py). The
    match request's `fitness_focus` ("general_fitness" - distinct from the profile's own
    closed-vocabulary FitnessFocus enum, and deliberately not a goal any seeded template lists)
    matches no seeded template's goals, so every template ties at a 0.0 goal factor under the
    fallback vector - that keeps bodyweight-full-body-x3 competitive for a top-3 slot (on its
    matching days/duration/beginner niche) regardless of how many other, differently-goaled
    templates are seeded. Explicitly weighting "general" via profile.goal_weights should then
    raise only its own goal factor.
    """
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 35,
        "fitness_focus": "general_fitness",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }

    await authenticated_client.post("/api/v1/users/profile", json={"fitness_focus": "general"})
    resp = await authenticated_client.post("/api/v1/programs/match", json=body)
    assert resp.status_code == 200
    without_vector = {m["slug"]: m["factors"]["goal"] for m in resp.json()["matches"]}
    assert "bodyweight-full-body-x3" in without_vector
    assert without_vector["bodyweight-full-body-x3"] == 0.0

    await authenticated_client.post(
        "/api/v1/users/profile",
        json={"fitness_focus": "general", "goal_weights": {"general": 0.9, "general_fitness": 0.1}},
    )
    resp = await authenticated_client.post("/api/v1/programs/match", json=body)
    assert resp.status_code == 200
    with_vector = {m["slug"]: m["factors"]["goal"] for m in resp.json()["matches"]}
    assert with_vector["bodyweight-full-body-x3"] == pytest.approx(0.9)
    assert with_vector["bodyweight-full-body-x3"] != without_vector["bodyweight-full-body-x3"]


async def _drafted_program_id(authenticated_client, user_environment) -> int:
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
    }
    r = await authenticated_client.post("/api/v1/programs/match", json=body)
    template_id = r.json()["matches"][0]["template_id"]
    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80, "bench_start": 60}}
    r = await authenticated_client.post("/api/v1/programs/draft", json=draft_body)
    assert r.status_code == 201
    return int(r.json()["program_id"])


@pytest.mark.asyncio
async def test_check_in_green_returns_no_effects(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)

    r = await authenticated_client.post(
        f"/api/v1/programs/{pid}/check-ins", json={"region": "knee", "status": "green", "note": "feeling fine"}
    )
    assert r.status_code == 201
    data = r.json()
    assert data["check_in"]["region"] == "knee"
    assert data["check_in"]["status"] == "green"
    assert data["check_in"]["note"] == "feeling fine"
    assert data["excluded"] is False
    assert data["consult_recommended"] is False
    assert data["draft_injury_record"] is None
    assert data["advisories"] == []


@pytest.mark.asyncio
async def test_check_in_two_ambers_triggers_regression_step(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)

    first = await authenticated_client.post(
        f"/api/v1/programs/{pid}/check-ins", json={"region": "knee", "status": "amber"}
    )
    assert first.status_code == 201
    assert first.json()["excluded"] is False

    second = await authenticated_client.post(
        f"/api/v1/programs/{pid}/check-ins", json={"region": "knee", "status": "amber"}
    )
    assert second.status_code == 201
    data = second.json()
    assert data["excluded"] is True
    assert data["advisories"][0]["code"] == "CHECK_IN_REGRESSION_STEP"


@pytest.mark.asyncio
async def test_check_in_red_returns_consult_message_and_draft_injury_record(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)

    r = await authenticated_client.post(
        f"/api/v1/programs/{pid}/check-ins", json={"region": "shoulder", "status": "red"}
    )
    assert r.status_code == 201
    data = r.json()
    assert data["excluded"] is True
    assert data["consult_recommended"] is True
    assert data["advisories"][0]["code"] == "CHECK_IN_RED_FLAG"
    assert data["advisories"][0]["severity"] == "error"
    draft = data["draft_injury_record"]
    assert draft["region"] == "shoulder"
    assert draft["phase"] == "acute"
    assert draft["severity"] == 3


@pytest.mark.asyncio
async def test_list_check_ins_returns_history_in_order(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)
    await authenticated_client.post(f"/api/v1/programs/{pid}/check-ins", json={"region": "knee", "status": "green"})
    await authenticated_client.post(f"/api/v1/programs/{pid}/check-ins", json={"region": "knee", "status": "amber"})

    r = await authenticated_client.get(f"/api/v1/programs/{pid}/check-ins")
    assert r.status_code == 200
    statuses = [c["status"] for c in r.json()]
    assert statuses == ["green", "amber"]


@pytest.mark.asyncio
async def test_check_in_404_for_foreign_program(client, auth_headers, db_session):
    other_user = User(
        email="other-checkin@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    from app.crud.program import save_program
    from app.models import ProgramStatus, WorkoutProgram

    other_program = WorkoutProgram(
        user_id=other_user.id,
        template_id=1,
        environment_id=1,
        name="Other's Program",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    await save_program(db_session, other_program)

    r = await client.post(
        f"/api/v1/programs/{other_program.id}/check-ins",
        json={"region": "knee", "status": "green"},
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_check_in_unauthorized(client):
    r = await client.post("/api/v1/programs/1/check-ins", json={"region": "knee", "status": "green"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_explain_template_returns_factors_and_tier(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)

    r = await authenticated_client.get(f"/api/v1/programs/{pid}/explain/template")
    assert r.status_code == 200
    data = r.json()
    assert data["tier"] == "best"
    assert set(data["factors"].keys()) == {
        "goal",
        "experience",
        "days",
        "duration",
        "movement_preference",
        "focus_complement",
        "periodization",
    }
    assert isinstance(data["fit_pct"], int)


@pytest.mark.asyncio
async def test_explain_template_404_for_foreign_program(client, auth_headers, db_session):
    other_user = User(
        email="other-explain-template@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    from app.crud.program import save_program
    from app.models import ProgramStatus, WorkoutProgram

    other_program = WorkoutProgram(
        user_id=other_user.id,
        template_id=1,
        environment_id=1,
        name="Other's Program",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    await save_program(db_session, other_program)

    r = await client.get(f"/api/v1/programs/{other_program.id}/explain/template", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_explain_slot_returns_factors_ledger_and_no_safety_note(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)
    program = await authenticated_client.get(f"/api/v1/programs/{pid}")
    we_id = program.json()["weeks"]["1"][0]["slots"][0]["workout_exercise_id"]

    r = await authenticated_client.get(f"/api/v1/programs/{pid}/explain/slot/{we_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["workout_exercise_id"] == we_id
    assert set(data["factors"].keys()) == {
        "variety",
        "priority_fit",
        "muscle_fit",
        "difficulty",
        "unilateral_balance",
        "movement_preference",
        "complementary_coverage",
    }
    assert data["ledger_contributions"]
    assert data["safety_note"] is None


@pytest.mark.asyncio
async def test_explain_slot_404_for_unknown_slot(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    pid = await _drafted_program_id(authenticated_client, user_environment)

    r = await authenticated_client.get(f"/api/v1/programs/{pid}/explain/slot/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_match_endpoint_returns_default_batch_size(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    """Match endpoint without limit/offset returns default batch size."""
    response = await authenticated_client.post(
        "/api/v1/programs/match",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert "total_count" in data
    assert "offset" in data
    assert "limit" in data
    assert data["offset"] == 0
    assert data["limit"] == 4  # Default batch size
    assert len(data["matches"]) <= 4


@pytest.mark.asyncio
async def test_match_endpoint_with_limit_and_offset(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    """Match endpoint accepts limit and offset query params."""
    response = await authenticated_client.post(
        "/api/v1/programs/match?limit=3&offset=4",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 4
    assert data["limit"] == 3
    assert len(data["matches"]) <= 3
    # Verify it's a slice, not all results
    assert data["total_count"] >= len(data["matches"])


@pytest.mark.asyncio
async def test_match_endpoint_rejects_negative_limit(
    authenticated_client, seeded_templates, seeded_exercises, user_environment
):
    """Match endpoint rejects negative limit."""
    response = await authenticated_client.post(
        "/api/v1/programs/match?limit=-1&offset=0",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == 422  # Validation error
