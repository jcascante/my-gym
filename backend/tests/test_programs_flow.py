import pytest


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
