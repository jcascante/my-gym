---
name: rest-api-design
description: Design consistent REST APIs following HTTP standards, proper status codes, error responses, and versioning
skills: [fastapi, rest, api-design]
allowed-tools: [Read, Edit, Write, TaskCreate]
---

# REST API Design Standards

Design consistent, predictable APIs following HTTP standards.

## API Structure

### URL Conventions

```
GET    /api/v1/users              # List users
POST   /api/v1/users              # Create user
GET    /api/v1/users/{id}         # Get specific user
PATCH  /api/v1/users/{id}         # Partial update
PUT    /api/v1/users/{id}         # Full replacement
DELETE /api/v1/users/{id}         # Delete user

GET    /api/v1/users/{id}/posts   # User's posts (nested)
POST   /api/v1/users/{id}/posts   # Create post for user

# Filtering
GET    /api/v1/users?status=active&page=1&limit=10

# Sorting
GET    /api/v1/users?sort=-created_at,name
```

### Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| **2xx** | Success | Request succeeded |
| 200 | OK | GET, PATCH, PUT success |
| 201 | Created | POST success (resource created) |
| 204 | No Content | DELETE success, no response body |
| **4xx** | Client Error | Client's fault |
| 400 | Bad Request | Invalid input/malformed request |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Authenticated but no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (email conflict) |
| 422 | Unprocessable Entity | Validation error |
| **5xx** | Server Error | Server's fault |
| 500 | Internal Server Error | Unexpected error |
| 503 | Service Unavailable | Temporarily down |

## Response Formats

### Success Response

```json
{
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### List Response (with pagination)

```json
{
  "data": [
    { "id": 1, "name": "John", "email": "john@example.com" },
    { "id": 2, "name": "Jane", "email": "jane@example.com" }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 42,
    "pages": 5
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      },
      {
        "field": "password",
        "message": "Must be at least 8 characters"
      }
    ]
  }
}
```

### NotFound Error

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User with id=999 not found"
  }
}
```

## FastAPI Implementation

### Response Models

```python
# app/schemas/responses.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class DataResponse(BaseModel, Generic[T]):
    data: T

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta

class ErrorDetail(BaseModel):
    field: str
    message: str

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None

# Specific models
class UserSchema(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreateSchema(BaseModel):
    name: str
    email: str
```

### Endpoints with Proper Responses

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, HTTPException, Query
from app.schemas import UserSchema, UserCreateSchema, DataResponse, PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=DataResponse[UserSchema], status_code=201)
async def create_user(
    user_data: UserCreateSchema,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new user"""
    existing = await db.execute(
        select(User).filter(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")
    
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return DataResponse(data=user)

@router.get("", response_model=PaginatedResponse[UserSchema])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    sort: str = Query("-created_at"),
    db: AsyncSession = Depends(get_async_db)
):
    """List all users with pagination and filtering"""
    query = select(User)
    
    # Filtering
    if status:
        query = query.filter(User.status == status)
    
    # Sorting
    for field in sort.split(','):
        if field.startswith('-'):
            query = query.order_by(getattr(User, field[1:]).desc())
        else:
            query = query.order_by(getattr(User, field))
    
    # Pagination
    total = await db.scalar(select(func.count()).select_from(User))
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    users = result.scalars().all()
    
    return PaginatedResponse(
        data=users,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    )

@router.get("/{user_id}", response_model=DataResponse[UserSchema])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific user"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return DataResponse(data=user)

@router.patch("/{user_id}", response_model=DataResponse[UserSchema])
async def update_user(
    user_id: int,
    user_data: UserUpdateSchema,
    db: AsyncSession = Depends(get_async_db)
):
    """Update user (partial)"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return DataResponse(data=user)

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete user"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    await db.delete(user)
    await db.commit()
    # 204 No Content - no response body
```

### Error Handling Middleware

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.schemas import ErrorResponse, ErrorDetail
from sqlalchemy.exc import IntegrityError

app = FastAPI()

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "CONFLICT",
                "message": "Resource already exists or constraint violated"
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )
```

## Versioning

### URL Versioning (Recommended)

```python
# app/api/v1/endpoints/users.py
router = APIRouter(prefix="/api/v1/users", tags=["users"])

# app/api/v2/endpoints/users.py
# router = APIRouter(prefix="/api/v2/users", tags=["users"])  # Future version
```

### Version Deprecation Pattern

```python
# Deprecate endpoint
@app.get("/api/v1/users/{id}")
async def get_user_v1(id: int):
    # Old endpoint
    return {"warning": "This endpoint is deprecated. Use /api/v2/users/{id}"}
```

## Best Practices

1. **Use HTTP verbs correctly**:
   - GET: Retrieve (safe, idempotent)
   - POST: Create (not idempotent)
   - PATCH: Partial update (idempotent)
   - PUT: Full replacement (idempotent)
   - DELETE: Remove (idempotent)

2. **Status codes matter**:
   - 201 for creation (POST)
   - 204 for deletion (DELETE)
   - 400 for bad input
   - 404 for not found
   - 409 for conflicts

3. **Consistent error format**:
   - Always return error in same structure
   - Include error code for client handling
   - Include details for validation errors

4. **Pagination**:
   - Always limit results (max 100)
   - Include total count
   - Use offset/limit or cursor-based

5. **Filtering & Sorting**:
   - Whitelist allowed fields
   - Support multiple sort fields
   - Use standard query param names

6. **Timestamps**:
   - Use ISO 8601 format (2024-01-15T10:30:00Z)
   - Store in UTC
   - Include created_at and updated_at

7. **Authentication**:
   - Use Bearer token in Authorization header
   - Return 401 for missing token
   - Return 403 for insufficient permissions

8. **Documentation**:
   - Use docstrings on endpoints
   - FastAPI auto-generates /docs
   - Keep API docs up to date

## Testing API Responses

```python
# tests/integration/test_users_api.py
@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test"}
    )
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_create_user_conflict(client: AsyncClient):
    # Create user
    await client.post("/api/v1/users", json={"email": "test@example.com", "name": "Test"})
    
    # Try to create duplicate
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test 2"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
```
