import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.models import User, UserProfile
from app.crud.user import create_or_update_user_profile, get_user_profile


@pytest.mark.asyncio
async def test_get_current_user_without_profile(
    client: AsyncClient, test_user: User, test_user_token: str
):
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name
    assert data["profile"] is None


@pytest.mark.asyncio
async def test_get_current_user_with_profile(
    client: AsyncClient,
    test_user: User,
    test_user_token: str,
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
        "equipment": "gym",
        "injuries_limitations": None,
        "short_term_goals": "Build muscle",
        "medium_term_goals": "Get stronger",
    }

    await create_or_update_user_profile(db, test_user.id, profile_data)

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
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
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_profile(
    client: AsyncClient, test_user: User, test_user_token: str
):
    profile_payload = {
        "age": 28,
        "gender": "female",
        "weight_kg": 65.0,
        "height_cm": 165,
        "activity_level": "very_active",
        "fitness_focus": "cardio",
        "experience_level": "beginner",
        "days_per_week": 5,
        "workout_duration_min": 45,
        "equipment": "home",
        "injuries_limitations": "None",
        "short_term_goals": "Lose weight",
        "medium_term_goals": "Improve endurance",
    }

    response = await client.post(
        "/api/v1/users/profile",
        json=profile_payload,
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is not None
    assert data["profile"]["age"] == 28
    assert data["profile"]["gender"] == "female"
    assert data["profile"]["weight_kg"] == 65.0
    assert data["profile"]["activity_level"] == "very_active"


@pytest.mark.asyncio
async def test_update_user_profile(
    client: AsyncClient,
    test_user: User,
    test_user_token: str,
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

    response = await client.post(
        "/api/v1/users/profile",
        json=updated_payload,
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["age"] == 31
    assert data["profile"]["weight_kg"] == 78.5
    assert data["profile"]["gender"] == "male"


@pytest.mark.asyncio
async def test_create_profile_with_null_values(
    client: AsyncClient, test_user: User, test_user_token: str
):
    profile_payload = {
        "age": 25,
        "gender": "male",
        "weight_kg": None,
        "height_cm": None,
        "activity_level": None,
        "fitness_focus": "strength",
    }

    response = await client.post(
        "/api/v1/users/profile",
        json=profile_payload,
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
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
    assert response.status_code == 403


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
