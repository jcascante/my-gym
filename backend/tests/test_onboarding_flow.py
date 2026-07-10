"""Integration tests for the onboarding flow."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


@pytest.mark.asyncio
async def test_first_time_user_flow(client: AsyncClient, db: AsyncSession):
    """Test complete flow for a first-time user: signup -> login -> no profile -> create profile."""

    # 1. User signs up
    signup_response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Smith",
        },
    )
    assert signup_response.status_code == 201
    user_id = signup_response.json()["id"]

    # 2. User logs in
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "newuser@example.com",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]

    # 3. Frontend fetches current user -> should have no profile
    user_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert user_response.status_code == 200
    user_data = user_response.json()
    assert user_data["email"] == "newuser@example.com"
    assert user_data["profile"] is None

    # 4. User completes onboarding -> creates profile
    profile_response = await client.post(
        "/api/v1/users/profile",
        json={
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
            "short_term_goals": "Lose weight",
            "medium_term_goals": "Improve endurance",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["profile"]["age"] == 28
    assert profile_data["profile"]["gender"] == "female"

    # 5. Frontend fetches current user again -> should now have profile
    user_with_profile = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert user_with_profile.status_code == 200
    updated_user = user_with_profile.json()
    assert updated_user["profile"] is not None
    assert updated_user["profile"]["age"] == 28


@pytest.mark.asyncio
async def test_returning_user_flow(
    client: AsyncClient, test_user: User, test_user_token: str, db: AsyncSession
):
    """Test flow for returning user with existing profile: login -> get profile -> can update."""

    # 1. Create profile for existing user
    initial_profile = await client.post(
        "/api/v1/users/profile",
        json={
            "age": 30,
            "gender": "male",
            "weight_kg": 80.0,
            "height_cm": 180,
            "activity_level": "moderately_active",
            "fitness_focus": "strength",
            "experience_level": "intermediate",
            "days_per_week": 4,
            "workout_duration_min": 60,
            "equipment": "gym",
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert initial_profile.status_code == 200

    # 2. "User logs out and logs back in"
    # (Simulate by creating new token for same user)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    new_token = login_response.json()["access_token"]

    # 3. Frontend fetches current user -> should have profile immediately
    user_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert user_response.status_code == 200
    user_data = user_response.json()
    assert user_data["profile"] is not None
    assert user_data["profile"]["age"] == 30
    assert user_data["profile"]["experience_level"] == "intermediate"

    # 4. User updates profile from settings
    update_response = await client.post(
        "/api/v1/users/profile",
        json={
            "age": 31,
            "weight_kg": 78.0,
        },
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["profile"]["age"] == 31
    assert updated_data["profile"]["weight_kg"] == 78.0
    assert updated_data["profile"]["gender"] == "male"


@pytest.mark.asyncio
async def test_profile_partial_updates(
    client: AsyncClient,
    test_user: User,
    test_user_token: str,
    db: AsyncSession,
):
    """Test that partial profile updates don't overwrite existing fields."""

    # Create initial profile with all fields
    initial = {
        "age": 25,
        "gender": "female",
        "weight_kg": 60.0,
        "height_cm": 165,
        "activity_level": "lightly_active",
        "fitness_focus": "flexibility",
        "experience_level": "beginner",
        "days_per_week": 3,
        "workout_duration_min": 30,
        "equipment": "home",
        "short_term_goals": "Get fit",
        "medium_term_goals": "Build strength",
    }

    create_response = await client.post(
        "/api/v1/users/profile",
        json=initial,
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert create_response.status_code == 200

    # Update only age and weight
    update_response = await client.post(
        "/api/v1/users/profile",
        json={"age": 26, "weight_kg": 62.0},
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()

    # Verify updated fields changed
    assert updated["profile"]["age"] == 26
    assert updated["profile"]["weight_kg"] == 62.0

    # Verify other fields remain unchanged
    assert updated["profile"]["gender"] == "female"
    assert updated["profile"]["height_cm"] == 165
    assert updated["profile"]["activity_level"] == "lightly_active"
    assert updated["profile"]["fitness_focus"] == "flexibility"
