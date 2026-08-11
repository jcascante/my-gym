import pytest


@pytest.mark.asyncio
async def test_list_templates_includes_duration_weeks_range(client, auth_headers, seeded_templates):
    r = await client.get("/api/v1/templates", headers=auth_headers)
    assert r.status_code == 200
    templates = r.json()["templates"]
    full_body = next(t for t in templates if t["slug"] == "full-body-x3")
    assert full_body["duration_weeks_default"] == 8
    assert full_body["duration_weeks_min"] == 4
    assert full_body["duration_weeks_max"] == 12
