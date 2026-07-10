import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    assert data["email"] == test_user.email

    # Tokens must be issued as httpOnly cookies, never in the response body.
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


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
    assert login_response.status_code == 200

    # The client's cookie jar now holds the refresh_token cookie from login.
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    client.cookies.set("refresh_token", "invalid_token")
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_no_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient, test_user: User):
    """An access token must not be usable as a refresh token."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123",
        },
    )
    access_token = login_response.cookies["access_token"]

    # Simulate an attacker submitting a stolen access token as the refresh token.
    client.cookies.set("refresh_token", access_token)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/v1/auth/logout")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_no_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
