import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.models import User


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, db: AsyncSession):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert "id" in data


@pytest.mark.asyncio
async def test_signup_email_already_exists(client: AsyncClient, db: AsyncSession, test_user: User):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user.email,
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Doe",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "invalid-email",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "user@example.com",
            "password": "short",
            "first_name": "John",
            "last_name": "Doe",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, test_user: User):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, test_user_token: str):
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_no_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 403
