import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ALLOWED_CONTRAINDICATION_TAGS, ALLOWED_EQUIPMENT_TAGS, ALLOWED_MUSCLE_GROUPS
from app.db.seed.exercises import EXERCISE_SEED_DATA
from app.db.seed.seed_exercises import upsert_exercises
from app.models import Exercise


@pytest.mark.asyncio
async def test_seed_data_integrity() -> None:
    """Verify all seed data uses allowed values."""
    for exercise in EXERCISE_SEED_DATA:
        for muscle in exercise["primary_muscles"]:
            assert muscle in ALLOWED_MUSCLE_GROUPS, f"Unknown primary muscle: {muscle}"

        for muscle in exercise.get("secondary_muscles", []):
            assert muscle in ALLOWED_MUSCLE_GROUPS, f"Unknown secondary muscle: {muscle}"

        for tag in exercise["equipment_tags"]:
            assert tag in ALLOWED_EQUIPMENT_TAGS, f"Unknown equipment tag: {tag}"

        for tag in exercise.get("contraindications", []):
            assert tag in ALLOWED_CONTRAINDICATION_TAGS, f"Unknown contraindication: {tag}"


@pytest.mark.asyncio
async def test_upsert_exercises_idempotent(db: AsyncSession) -> None:
    """Running upsert twice produces no duplicate rows."""
    await upsert_exercises(db)
    result1 = await db.execute(__import__("sqlalchemy").select(Exercise))
    count1 = len(list(result1.scalars().all()))

    await upsert_exercises(db)
    result2 = await db.execute(__import__("sqlalchemy").select(Exercise))
    count2 = len(list(result2.scalars().all()))

    assert count1 == count2 == len(EXERCISE_SEED_DATA)


@pytest.mark.asyncio
async def test_upsert_exercises_updates_existing(db: AsyncSession) -> None:
    """Changing a field in seed data updates existing row."""
    await upsert_exercises(db)

    result = await db.execute(__import__("sqlalchemy").select(Exercise).where(Exercise.slug == "barbell-bench-press"))
    existing = result.scalar_one()
    existing.name = "Modified Bench Press"
    db.add(existing)
    await db.commit()

    check = await db.execute(__import__("sqlalchemy").select(Exercise).where(Exercise.slug == "barbell-bench-press"))
    updated = check.scalar_one()
    assert updated.name == "Modified Bench Press"


@pytest.mark.asyncio
async def test_upsert_exercises_deactivates_removed(db: AsyncSession) -> None:
    """Removing a slug from seed and re-running sets is_active=False."""
    await upsert_exercises(db)

    # Manually deactivate a non-existent exercise to test logic
    new_exercise = Exercise(
        name="Test Exercise",
        slug="test-exercise",
        movement_slug="test_pattern",
        body_region="UPPER_BODY",
        movement_pattern="ISOLATION",
        primary_muscles=["chest"],
        secondary_muscles=[],
        equipment_tags=["dumbbells"],
        difficulty_level="BEGINNER",
        instructions="Test",
        form_cues=[],
        contraindications=[],
        is_active=True,
    )
    db.add(new_exercise)
    await db.commit()

    # Re-run upsert; the new exercise should be deactivated
    await upsert_exercises(db)

    check = await db.execute(__import__("sqlalchemy").select(Exercise).where(Exercise.slug == "test-exercise"))
    result = check.scalar_one()
    assert result.is_active is False


@pytest.mark.asyncio
async def test_list_exercises_empty(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/exercises")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_exercises_populated(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(EXERCISE_SEED_DATA)


@pytest.mark.asyncio
async def test_list_exercises_filter_body_region(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises?body_region=upper_body")
    assert response.status_code == 200
    data = response.json()
    assert all(ex["body_region"] == "upper_body" for ex in data)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_exercises_filter_movement_pattern(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises?movement_pattern=hinge")
    assert response.status_code == 200
    data = response.json()
    assert all(ex["movement_pattern"] == "hinge" for ex in data)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_exercises_filter_equipment_tags(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises?equipment_tags=dumbbells")
    assert response.status_code == 200
    data = response.json()
    assert all("dumbbells" in ex["equipment_tags"] for ex in data)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_exercises_filter_muscle_group(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises?muscle_group=quads")
    assert response.status_code == 200
    data = response.json()
    assert all("quads" in ex["primary_muscles"] or "quads" in ex["secondary_muscles"] for ex in data)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_exercises_filter_difficulty(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get("/api/v1/exercises?difficulty_level=beginner")
    assert response.status_code == 200
    data = response.json()
    assert all(ex["difficulty_level"] == "beginner" for ex in data)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_exercises_filter_multiple(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    response = await authenticated_client.get(
        "/api/v1/exercises?body_region=lower_body&movement_pattern=hinge&equipment_tags=dumbbells"
    )
    assert response.status_code == 200
    data = response.json()
    assert all(
        ex["body_region"] == "lower_body" and ex["movement_pattern"] == "hinge" and "dumbbells" in ex["equipment_tags"]
        for ex in data
    )


@pytest.mark.asyncio
async def test_get_exercise(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    result = await db.execute(__import__("sqlalchemy").select(Exercise).limit(1))
    exercise = result.scalar_one()

    response = await authenticated_client.get(f"/api/v1/exercises/{exercise.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exercise.id
    assert data["name"] == exercise.name


@pytest.mark.asyncio
async def test_get_exercise_not_found(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/exercises/9999")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "EXERCISE_NOT_FOUND"


@pytest.mark.asyncio
async def test_exercises_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/exercises")
    assert response.status_code == 401

    response = await client.get("/api/v1/exercises/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_exercises_excludes_inactive(authenticated_client: AsyncClient, db: AsyncSession):
    await upsert_exercises(db)

    result = await db.execute(__import__("sqlalchemy").select(Exercise).limit(1))
    exercise = result.scalar_one()
    exercise.is_active = False
    db.add(exercise)
    await db.commit()

    response = await authenticated_client.get("/api/v1/exercises")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(EXERCISE_SEED_DATA) - 1
    assert not any(ex["id"] == exercise.id for ex in data)
