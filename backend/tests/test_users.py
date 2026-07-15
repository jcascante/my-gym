import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud.user import create_or_update_user_profile, get_user_profile
from app.models import User


@pytest.mark.asyncio
async def test_get_current_user_without_profile(authenticated_client: AsyncClient, test_user: User):
    response = await authenticated_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name
    assert data["profile"] is None


@pytest.mark.asyncio
async def test_get_current_user_with_profile(
    authenticated_client: AsyncClient,
    test_user: User,
    db: AsyncSession,
):
    profile_data = {
        "age": 30,
        "gender": "male",
        "weight_kg": 75.5,
        "height_cm": 180,
        "activity_level": "moderately_active",
        "fitness_focus": "strength",
        "experience_level": "intermediate",
        "days_per_week": 4,
        "workout_duration_min": 60,
        "injuries_limitations": None,
        "short_term_goals": "Build muscle",
        "medium_term_goals": "Get stronger",
    }

    await create_or_update_user_profile(db, test_user.id, profile_data)

    response = await authenticated_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["profile"] is not None
    assert data["profile"]["age"] == 30
    assert data["profile"]["gender"] == "male"
    assert data["profile"]["weight_kg"] == 75.5


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_user_profile(authenticated_client: AsyncClient, test_user: User):
    profile_payload = {
        "age": 28,
        "gender": "female",
        "weight_kg": 65.0,
        "height_cm": 165,
        "activity_level": "very_active",
        "fitness_focus": "endurance",
        "experience_level": "beginner",
        "days_per_week": 5,
        "workout_duration_min": 45,
        "injuries_limitations": "None",
        "short_term_goals": "Lose weight",
        "medium_term_goals": "Improve endurance",
    }

    response = await authenticated_client.post("/api/v1/users/profile", json=profile_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is not None
    assert data["profile"]["age"] == 28
    assert data["profile"]["gender"] == "female"
    assert data["profile"]["weight_kg"] == 65.0
    assert data["profile"]["activity_level"] == "very_active"


@pytest.mark.asyncio
async def test_update_user_profile(
    authenticated_client: AsyncClient,
    test_user: User,
    db: AsyncSession,
):
    initial_profile = {
        "age": 30,
        "gender": "male",
        "weight_kg": 80.0,
        "height_cm": 180,
    }
    await create_or_update_user_profile(db, test_user.id, initial_profile)

    updated_payload = {
        "age": 31,
        "weight_kg": 78.5,
    }

    response = await authenticated_client.post("/api/v1/users/profile", json=updated_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["age"] == 31
    assert data["profile"]["weight_kg"] == 78.5
    assert data["profile"]["gender"] == "male"


@pytest.mark.asyncio
async def test_create_profile_with_null_values(authenticated_client: AsyncClient, test_user: User):
    profile_payload = {
        "age": 25,
        "gender": "male",
        "weight_kg": None,
        "height_cm": None,
        "activity_level": None,
        "fitness_focus": "strength",
    }

    response = await authenticated_client.post("/api/v1/users/profile", json=profile_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["age"] == 25
    assert data["profile"]["fitness_focus"] == "strength"


@pytest.mark.asyncio
async def test_create_profile_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/v1/users/profile",
        json={"age": 30},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_crud_get_user_profile_not_exists(db: AsyncSession):
    result = await get_user_profile(db, 9999)
    assert result is None


@pytest.mark.asyncio
async def test_crud_create_or_update_new_profile(db: AsyncSession):
    user = User(
        email="test2@example.com",
        password_hash=hash_password("password123"),
        first_name="Test",
        last_name="User2",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile_data = {
        "age": 35,
        "gender": "male",
        "weight_kg": 90.0,
        "fitness_focus": "strength",
    }

    profile = await create_or_update_user_profile(db, user.id, profile_data)

    assert profile.user_id == user.id
    assert profile.age == 35
    assert profile.gender == "male"
    assert profile.weight_kg == 90.0
    assert profile.fitness_focus == "strength"


@pytest.mark.asyncio
async def test_crud_update_existing_profile(db: AsyncSession):
    user = User(
        email="test3@example.com",
        password_hash=hash_password("password123"),
        first_name="Test",
        last_name="User3",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    initial_data = {
        "age": 25,
        "gender": "female",
        "weight_kg": 60.0,
    }
    profile = await create_or_update_user_profile(db, user.id, initial_data)
    initial_id = profile.id

    update_data = {"age": 26, "weight_kg": 62.0}
    updated_profile = await create_or_update_user_profile(db, user.id, update_data)

    assert updated_profile.id == initial_id
    assert updated_profile.age == 26
    assert updated_profile.weight_kg == 62.0
    assert updated_profile.gender == "female"


@pytest.mark.asyncio
async def test_update_profile_set_field_to_null(authenticated_client: AsyncClient, test_user: User):
    """Test that setting a profile field to null actually persists the null value"""
    initial_payload = {
        "age": 30,
        "gender": "male",
        "weight_kg": 80.0,
        "height_cm": 180,
        "fitness_focus": "strength",
    }

    response = await authenticated_client.post("/api/v1/users/profile", json=initial_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["age"] == 30
    assert data["profile"]["fitness_focus"] == "strength"

    updated_payload = {
        "age": 30,
        "gender": "male",
        "weight_kg": 80.0,
        "height_cm": 180,
        "fitness_focus": None,
    }

    response = await authenticated_client.post("/api/v1/users/profile", json=updated_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["age"] == 30
    assert data["profile"]["fitness_focus"] is None
