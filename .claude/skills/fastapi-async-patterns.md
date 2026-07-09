---
name: fastapi-async-patterns
description: Write efficient FastAPI endpoints using async/await patterns, proper dependency injection, and structured error handling
skills: [fastapi, async, pydantic]
allowed-tools: [Read, Edit, Write, TaskCreate]
---

# FastAPI Async Patterns Skill

FastAPI is async-first. All I/O operations must use async/await to avoid blocking the event loop.

## Proper Endpoint Structure

### ❌ DON'T (Blocking I/O)
```python
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()  # BLOCKS!
    return user
```

### ✅ DO (Non-blocking async)
```python
@app.get("/users/{user_id}", response_model=UserSchema)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Dependency Injection Pattern

```python
# app/api/deps.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_maker

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> UserSchema:
    user = await get_user_by_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
```

## CRUD Operations (Async)

```python
# app/crud/users.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserCRUD:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int):
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(db: AsyncSession, user_data: UserCreate) -> User:
        db_user = User(**user_data.dict())
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    @staticmethod
    async def update(db: AsyncSession, user_id: int, update_data: UserUpdate) -> User:
        db_user = await UserCRUD.get_by_id(db, user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(db_user, key, value)
        
        await db.commit()
        await db.refresh(db_user)
        return db_user
```

## Service Layer (Business Logic)

```python
# app/services/users.py
from app.crud.users import UserCRUD
from app.schemas import UserCreate, UserUpdate, UserSchema

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.crud = UserCRUD()
    
    async def create_user(self, user_data: UserCreate) -> UserSchema:
        # Validation
        existing = await self.crud.get_by_email(self.db, user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Business logic
        user = await self.crud.create(self.db, user_data)
        
        # Side effects (send email, etc.)
        # await send_welcome_email(user.email)
        
        return UserSchema.from_orm(user)
```

## Endpoint with Service

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserSchema, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    return await service.create_user(user_data)

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Error Handling

```python
# app/core/errors.py
from fastapi import HTTPException

class ApplicationError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundError(ApplicationError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=404,
            detail=f"{resource} with {identifier} not found"
        )

class ConflictError(ApplicationError):
    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)

class ValidationError(ApplicationError):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)

# Usage
async def get_user(user_id: int, db: AsyncSession):
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("User", f"id={user_id}")
    return user
```

## Exception Handlers

```python
# app/main.py
from fastapi import FastAPI
from app.core.errors import ApplicationError

app = FastAPI()

@app.exception_handler(ApplicationError)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

## Parallel Async Operations

```python
# Run multiple async operations concurrently
import asyncio

async def create_user_with_profile(
    user_data: UserCreate,
    profile_data: ProfileCreate,
    db: AsyncSession
):
    # Parallel execution
    user_task = create_user(db, user_data)
    profile_task = create_profile(db, profile_data)
    
    user, profile = await asyncio.gather(user_task, profile_task)
    
    return {"user": user, "profile": profile}
```

## Testing Async Endpoints

```python
# tests/integration/test_users.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, db: AsyncSession):
    # client is AsyncClient, db is AsyncSession fixture
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test"}
    )
    assert response.status_code == 201
    
    # Verify in database
    result = await db.execute(select(User).filter(User.email == "test@example.com"))
    assert result.scalar_one_or_none() is not None
```

## Configuration

**app/database.py**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
```

## Best Practices Checklist

- ✅ Use `async def` for all endpoint functions
- ✅ Use `AsyncSession` for database operations
- ✅ Use `await` for all I/O operations (DB, HTTP, file, etc.)
- ✅ Leverage `asyncio.gather()` for parallel operations
- ✅ Never block the event loop with sync operations
- ✅ Use proper type hints with async types
- ✅ Handle exceptions with custom error classes
- ✅ Write tests with `pytest-asyncio`
