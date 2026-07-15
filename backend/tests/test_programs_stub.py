import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud.training_environment import create_training_environment
from app.models import User

VALID_PAYLOAD = {
    "days_per_week": 4,
    "preferred_days": ["monday", "wednesday", "friday", "saturday"],
    "session_duration_min": 60,
    "start_date": "2026-08-01",
    "focus_areas": ["push", "pull", "legs"],
    "weight_unit": "kg",
    "available_weight_increments": [1.25, 2.5, 5],
    "progression_style": "consistent",
}


@pytest.mark.asyncio
async def test_create_program_returns_501_for_owned_environment(
    authenticated_client: AsyncClient, test_user: User, db: AsyncSession
):
    environment = await create_training_environment(
        db, test_user.id, {"name": "Gym", "environment_type": "commercial_gym", "equipment_tags": []}
    )

    response = await authenticated_client.post(
        "/api/v1/programs", json={**VALID_PAYLOAD, "environment_id": environment.id}
    )
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_create_program_404_for_missing_environment(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/v1/programs", json={**VALID_PAYLOAD, "environment_id": 9999})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_program_404_for_foreign_environment(authenticated_client: AsyncClient, db: AsyncSession):
    other_user = User(
        email="other-program@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    other_environment = await create_training_environment(
        db, other_user.id, {"name": "Other's Gym", "environment_type": "home", "equipment_tags": []}
    )

    response = await authenticated_client.post(
        "/api/v1/programs", json={**VALID_PAYLOAD, "environment_id": other_environment.id}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_program_422_for_malformed_payload(authenticated_client: AsyncClient):
    incomplete_payload = {"environment_id": 1}
    response = await authenticated_client.post("/api/v1/programs", json=incomplete_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_program_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/programs", json={**VALID_PAYLOAD, "environment_id": 1})
    assert response.status_code == 401
