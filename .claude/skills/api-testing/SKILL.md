---
name: api-testing
description: Test FastAPI endpoints with comprehensive testing strategy including unit, integration, and fixture-based tests
skills: [pytest, pytest-asyncio, httpx, testing]
allowed-tools: [Bash, Read, Edit, Write, TaskCreate]
---

# API Testing Skill

When testing FastAPI endpoints, follow this pattern:

## Test Structure
1. **Unit tests** (tests/unit/): Test individual functions, CRUD operations in isolation
2. **Integration tests** (tests/integration/): Full request/response cycle with database
3. **Use fixtures**: Database session, client, test data

## Example Pattern

```python
# tests/integration/test_users.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.schemas import UserCreate

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_create_user(client):
    # Arrange
    user_data = UserCreate(email="test@example.com", name="Test")
    
    # Act
    response = await client.post("/api/v1/users", json=user_data.dict())
    
    # Assert
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

## Tools & Commands
- `pytest tests/integration/ -v`: Run all integration tests
- `pytest tests/unit/ -v`: Run unit tests only
- `pytest --cov=app`: Generate coverage report
- Use `pytest-asyncio` for async endpoint testing
- Use `httpx.AsyncClient` for testing async FastAPI

## Best Practices
- Test happy path AND error cases (400, 404, 500)
- Use factories (factory_boy) for test data
- Mock external APIs/services
- Cleanup database state after each test
- Separate concerns: one test per behavior
