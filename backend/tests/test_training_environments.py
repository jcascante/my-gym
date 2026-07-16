import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud.training_environment import create_training_environment
from app.models import User


@pytest.mark.asyncio
async def test_list_training_environments_empty(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/training-environments")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_training_environment(authenticated_client: AsyncClient):
    payload = {
        "name": "Home Gym",
        "environment_type": "home",
        "equipment_tags": ["dumbbells", "pull_up_bar"],
        "is_default": True,
    }
    response = await authenticated_client.post("/api/v1/training-environments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Home Gym"
    assert data["environment_type"] == "home"
    assert data["equipment_tags"] == ["dumbbells", "pull_up_bar"]
    assert data["is_default"] is True


@pytest.mark.asyncio
async def test_create_training_environment_new_archetypes(authenticated_client: AsyncClient):
    for environment_type in ("powerlifting_gym", "strength_gym"):
        payload = {
            "name": f"{environment_type} test",
            "environment_type": environment_type,
            "equipment_tags": ["barbell", "squat_rack", "bench"],
        }
        response = await authenticated_client.post("/api/v1/training-environments", json=payload)
        assert response.status_code == 201, response.text
        assert response.json()["environment_type"] == environment_type


@pytest.mark.asyncio
async def test_create_training_environment_rejects_unknown_tag(authenticated_client: AsyncClient):
    payload = {
        "name": "Bad Gym",
        "environment_type": "home",
        "equipment_tags": ["not_a_real_tag"],
    }
    response = await authenticated_client.post("/api/v1/training-environments", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_training_environments_populated(
    authenticated_client: AsyncClient, test_user: User, db: AsyncSession
):
    await create_training_environment(
        db, test_user.id, {"name": "Gym", "environment_type": "commercial_gym", "equipment_tags": []}
    )
    await create_training_environment(
        db, test_user.id, {"name": "Home", "environment_type": "home", "equipment_tags": []}
    )

    response = await authenticated_client.get("/api/v1/training-environments")
    assert response.status_code == 200
    names = {env["name"] for env in response.json()}
    assert names == {"Gym", "Home"}


@pytest.mark.asyncio
async def test_get_training_environment(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    environment = await create_training_environment(
        db, test_user.id, {"name": "Box", "environment_type": "crossfit_box", "equipment_tags": []}
    )

    response = await authenticated_client.get(f"/api/v1/training-environments/{environment.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Box"


@pytest.mark.asyncio
async def test_get_training_environment_not_found(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/training-environments/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_training_environment(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    environment = await create_training_environment(
        db, test_user.id, {"name": "Gym", "environment_type": "commercial_gym", "equipment_tags": []}
    )

    response = await authenticated_client.patch(
        f"/api/v1/training-environments/{environment.id}",
        json={"name": "Updated Gym"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Gym"
    assert data["environment_type"] == "commercial_gym"


@pytest.mark.asyncio
async def test_delete_training_environment(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    environment = await create_training_environment(
        db, test_user.id, {"name": "Gym", "environment_type": "commercial_gym", "equipment_tags": []}
    )

    response = await authenticated_client.delete(f"/api/v1/training-environments/{environment.id}")
    assert response.status_code == 204

    follow_up = await authenticated_client.get(f"/api/v1/training-environments/{environment.id}")
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_default_flag_exclusivity(authenticated_client: AsyncClient, test_user: User, db: AsyncSession):
    first = await create_training_environment(
        db,
        test_user.id,
        {"name": "Gym", "environment_type": "commercial_gym", "equipment_tags": [], "is_default": True},
    )

    response = await authenticated_client.post(
        "/api/v1/training-environments",
        json={"name": "Home", "environment_type": "home", "equipment_tags": [], "is_default": True},
    )
    assert response.status_code == 201

    first_response = await authenticated_client.get(f"/api/v1/training-environments/{first.id}")
    assert first_response.json()["is_default"] is False


@pytest.mark.asyncio
async def test_environments_are_scoped_to_owner(authenticated_client: AsyncClient, db: AsyncSession):
    other_user = User(
        email="other@example.com",
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

    get_response = await authenticated_client.get(f"/api/v1/training-environments/{other_environment.id}")
    assert get_response.status_code == 404

    update_response = await authenticated_client.patch(
        f"/api/v1/training-environments/{other_environment.id}", json={"name": "Hijacked"}
    )
    assert update_response.status_code == 404

    delete_response = await authenticated_client.delete(f"/api/v1/training-environments/{other_environment.id}")
    assert delete_response.status_code == 404

    list_response = await authenticated_client.get("/api/v1/training-environments")
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_training_environments_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/training-environments")
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/training-environments",
        json={"name": "Gym", "environment_type": "home", "equipment_tags": []},
    )
    assert response.status_code == 401
