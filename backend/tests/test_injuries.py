from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud.injury import create_injury_record
from app.models import User


def _payload(**overrides: object) -> dict:
    """JSON-serializable payload for HTTP requests (reported_at as ISO string)."""
    payload = {
        "region": "shoulder",
        "condition": "tendinopathy",
        "phase": "rehabilitating",
        "provocations": ["overhead", "loaded_spinal_flexion"],
        "severity": 2,
        "reported_at": "2026-01-15",
        "source": "user_reported",
    }
    payload.update(overrides)
    return payload


def _crud_payload(**overrides: object) -> dict:
    """Payload for direct CRUD calls, bypassing Pydantic (reported_at as a date object)."""
    payload = _payload(**overrides)
    if isinstance(payload["reported_at"], str):
        payload["reported_at"] = date.fromisoformat(payload["reported_at"])
    return payload


@pytest.mark.asyncio
async def test_list_injury_records_empty(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/users/me/injuries")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_injury_record(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/v1/users/me/injuries", json=_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["region"] == "shoulder"
    assert data["condition"] == "tendinopathy"
    assert data["phase"] == "rehabilitating"
    assert data["provocations"] == ["overhead", "loaded_spinal_flexion"]
    assert data["severity"] == 2
    assert data["reported_at"] == "2026-01-15"
    assert data["source"] == "user_reported"


@pytest.mark.asyncio
async def test_create_injury_record_defaults_provocations(authenticated_client: AsyncClient):
    payload = _payload()
    del payload["provocations"]
    response = await authenticated_client.post("/api/v1/users/me/injuries", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["provocations"] == []


@pytest.mark.asyncio
async def test_create_injury_record_rejects_invalid_severity(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/v1/users/me/injuries", json=_payload(severity=5))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_injury_record_rejects_invalid_region(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/v1/users/me/injuries", json=_payload(region="spine"))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_injury_record_rejects_invalid_provocation(authenticated_client: AsyncClient):
    response = await authenticated_client.post(
        "/api/v1/users/me/injuries", json=_payload(provocations=["not_a_real_provocation"])
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_injury_records_populated(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    await create_injury_record(
        db,
        test_user.id,
        _crud_payload(
            region="knee",
            condition="post_surgical",
            phase="acute",
            provocations=["deep_knee_flexion"],
            severity=3,
            reported_at="2026-02-01",
            source="professional_cleared",
        ),
    )
    await create_injury_record(
        db,
        test_user.id,
        _crud_payload(
            region="wrist",
            condition="chronic_recurrent",
            phase="cleared",
            provocations=[],
            severity=1,
            reported_at="2026-03-01",
            source="user_reported",
        ),
    )

    response = await authenticated_client.get("/api/v1/users/me/injuries")
    assert response.status_code == 200
    regions = {record["region"] for record in response.json()}
    assert regions == {"knee", "wrist"}


@pytest.mark.asyncio
async def test_get_injury_record(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    injury = await create_injury_record(db, test_user.id, _crud_payload())

    response = await authenticated_client.get(f"/api/v1/users/me/injuries/{injury.id}")
    assert response.status_code == 200
    assert response.json()["region"] == "shoulder"


@pytest.mark.asyncio
async def test_get_injury_record_not_found(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/users/me/injuries/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_injury_record(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    injury = await create_injury_record(db, test_user.id, _crud_payload())

    response = await authenticated_client.patch(
        f"/api/v1/users/me/injuries/{injury.id}",
        json={"phase": "cleared", "severity": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "cleared"
    assert data["severity"] == 1
    assert data["region"] == "shoulder"


@pytest.mark.asyncio
async def test_delete_injury_record(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    injury = await create_injury_record(db, test_user.id, _crud_payload())

    response = await authenticated_client.delete(f"/api/v1/users/me/injuries/{injury.id}")
    assert response.status_code == 204

    follow_up = await authenticated_client.get(f"/api/v1/users/me/injuries/{injury.id}")
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_injury_records_are_scoped_to_owner(authenticated_client: AsyncClient, db: AsyncSession):
    other_user = User(
        email="other-injury@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    other_injury = await create_injury_record(db, other_user.id, _crud_payload())

    get_response = await authenticated_client.get(f"/api/v1/users/me/injuries/{other_injury.id}")
    assert get_response.status_code == 404

    update_response = await authenticated_client.patch(
        f"/api/v1/users/me/injuries/{other_injury.id}", json={"severity": 3}
    )
    assert update_response.status_code == 404

    delete_response = await authenticated_client.delete(f"/api/v1/users/me/injuries/{other_injury.id}")
    assert delete_response.status_code == 404

    list_response = await authenticated_client.get("/api/v1/users/me/injuries")
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_injuries_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/me/injuries")
    assert response.status_code == 401

    response = await client.post("/api/v1/users/me/injuries", json=_payload())
    assert response.status_code == 401
