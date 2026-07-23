import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud import logging as crud_logging
from app.models import ProgramStatus, User, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.logging import UserWorkoutLogCreate, WorkoutSetLogCreate
from app.services.auth import create_tokens


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second user for isolation testing."""
    user = User(
        email="other@example.com",
        password_hash=hash_password("password123"),
        first_name="Other",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user_token(other_user: User) -> str:
    """Create token for second user."""
    tokens = create_tokens(other_user.id)
    return tokens["access_token"]


@pytest.fixture
async def other_user_headers(other_user_token: str) -> dict[str, str]:
    """Auth headers for second user."""
    return {"Authorization": f"Bearer {other_user_token}"}


@pytest.fixture
async def test_program_with_workout(
    db_session: AsyncSession, test_user: User
) -> tuple[WorkoutProgram, Workout, WorkoutExercise]:
    """Create a complete workout program with exercises for testing."""
    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=1,
        environment_id=1,
        name="Test Program",
        status=ProgramStatus.ACTIVE,
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(
        program_id=program.id,
        key="upper_a",
        name="Upper A",
        focus="chest,back",
        order=1,
    )
    db_session.add(workout)
    await db_session.flush()

    exercise = WorkoutExercise(
        workout_id=workout.id,
        order=1,
        exercise_id=1,
        fills_rule={"pattern": "horizontal_push"},
        sets=3,
        reps_min=8,
        reps_max=12,
        base_load=60.0,
        rest_seconds=120,
        scheme_key="main",
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(exercise)
    await db_session.commit()
    await db_session.refresh(program)
    await db_session.refresh(workout)
    await db_session.refresh(exercise)

    return program, workout, exercise


@pytest.mark.asyncio
async def test_create_workout_log(db_session: AsyncSession, test_user: User, test_program_with_workout: tuple):
    """Test creating a workout session log with all fields."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(
        readiness=4,
        notes="Feeling strong today",
    )

    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.workout_id == workout.id
    assert log.readiness == 4
    assert log.notes == "Feeling strong today"
    assert log.created_at is not None


@pytest.mark.asyncio
async def test_create_workout_log_without_readiness(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple
):
    """Test creating a workout log with nullable readiness."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(
        readiness=None,
        notes="Just checking in",
    )

    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.readiness is None
    assert log.notes == "Just checking in"


@pytest.mark.asyncio
async def test_get_workout_log(db_session: AsyncSession, test_user: User, test_program_with_workout: tuple):
    """Test retrieving a specific workout log."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(readiness=3)
    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    retrieved = await crud_logging.get_workout_log(db_session, log.id, test_user.id)

    assert retrieved is not None
    assert retrieved.id == log.id
    assert retrieved.user_id == test_user.id
    assert retrieved.readiness == 3


@pytest.mark.asyncio
async def test_get_workout_log_wrong_user(
    db_session: AsyncSession, test_user: User, other_user: User, test_program_with_workout: tuple
):
    """Test that users cannot access other users' workout logs."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(readiness=4)
    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    # Attempt to retrieve as other user
    retrieved = await crud_logging.get_workout_log(db_session, log.id, other_user.id)

    assert retrieved is None


@pytest.mark.asyncio
async def test_get_user_workout_logs(db_session: AsyncSession, test_user: User, test_program_with_workout: tuple):
    """Test listing user's workout logs ordered by session_date descending."""
    _, workout, _ = test_program_with_workout

    # Create multiple logs
    for i in range(3):
        data = UserWorkoutLogCreate(readiness=i + 1)
        await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)

    await db_session.commit()

    logs = await crud_logging.get_user_workout_logs(db_session, test_user.id)

    assert len(logs) == 3
    # Verify ordered by session_date descending
    for i in range(len(logs) - 1):
        assert logs[i].session_date >= logs[i + 1].session_date


@pytest.mark.asyncio
async def test_get_user_workout_logs_pagination(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple
):
    """Test pagination with limit and offset."""
    _, workout, _ = test_program_with_workout

    # Create 5 logs
    for i in range(5):
        data = UserWorkoutLogCreate(readiness=1)
        await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)

    await db_session.commit()

    # Get first 2
    page1 = await crud_logging.get_user_workout_logs(db_session, test_user.id, limit=2, offset=0)
    assert len(page1) == 2

    # Get next 2
    page2 = await crud_logging.get_user_workout_logs(db_session, test_user.id, limit=2, offset=2)
    assert len(page2) == 2

    # Get remaining
    page3 = await crud_logging.get_user_workout_logs(db_session, test_user.id, limit=2, offset=4)
    assert len(page3) == 1

    # Verify no duplicates across pages
    all_ids = {log.id for page in [page1, page2, page3] for log in page}
    assert len(all_ids) == 5


@pytest.mark.asyncio
async def test_append_set_log(db_session: AsyncSession, test_user: User, test_program_with_workout: tuple):
    """Test appending a set performance log."""
    _, workout, exercise = test_program_with_workout

    data = WorkoutSetLogCreate(
        workout_id=workout.id,
        workout_exercise_id=exercise.id,
        set_number=1,
        actual_weight=70.0,
        actual_reps=10,
        actual_rpe=8.0,
    )

    log = await crud_logging.append_set_log(db_session, test_user.id, data)
    await db_session.commit()

    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.workout_id == workout.id
    assert log.workout_exercise_id == exercise.id
    assert log.set_number == 1
    assert log.actual_weight == 70.0
    assert log.actual_reps == 10
    assert log.actual_rpe == 8.0


@pytest.mark.asyncio
async def test_get_set_logs(db_session: AsyncSession, test_user: User, test_program_with_workout: tuple):
    """Test retrieving all set logs for a workout, ordered by exercise and set number."""
    _, workout, exercise = test_program_with_workout

    # Add a second exercise to the workout
    exercise2 = WorkoutExercise(
        workout_id=workout.id,
        order=2,
        exercise_id=2,
        fills_rule={"pattern": "vertical_pull"},
        sets=3,
        reps_min=6,
        reps_max=8,
        base_load=50.0,
        rest_seconds=150,
        scheme_key="main",
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(exercise2)
    await db_session.flush()

    # Add set logs for both exercises
    for set_num in [1, 2, 3]:
        data1 = WorkoutSetLogCreate(
            workout_id=workout.id,
            workout_exercise_id=exercise.id,
            set_number=set_num,
            actual_weight=70.0 + set_num,
            actual_reps=10,
            actual_rpe=7.0,
        )
        await crud_logging.append_set_log(db_session, test_user.id, data1)

        data2 = WorkoutSetLogCreate(
            workout_id=workout.id,
            workout_exercise_id=exercise2.id,
            set_number=set_num,
            actual_weight=50.0 + set_num,
            actual_reps=8,
            actual_rpe=7.5,
        )
        await crud_logging.append_set_log(db_session, test_user.id, data2)

    await db_session.commit()

    logs = await crud_logging.get_set_logs(db_session, workout.id, test_user.id)

    assert len(logs) == 6  # 3 sets x 2 exercises
    # Verify ordered by exercise_id, then set_number
    for i in range(len(logs) - 1):
        if logs[i].workout_exercise_id == logs[i + 1].workout_exercise_id:
            assert logs[i].set_number <= logs[i + 1].set_number


@pytest.mark.asyncio
async def test_endpoint_create_session_log(authenticated_client: AsyncClient, test_program_with_workout: tuple):
    """Test POST /workouts/{id}/logs endpoint."""
    _, workout, _ = test_program_with_workout

    response = await authenticated_client.post(
        f"/api/v1/workouts/{workout.id}/logs",
        json={
            "readiness": 4,
            "notes": "Felt good",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["workout_id"] == workout.id
    assert data["readiness"] == 4
    assert data["notes"] == "Felt good"


@pytest.mark.asyncio
async def test_endpoint_create_session_log_unauthorized(client: AsyncClient, test_program_with_workout: tuple):
    """Test that unauthenticated requests are rejected."""
    _, workout, _ = test_program_with_workout

    response = await client.post(
        f"/api/v1/workouts/{workout.id}/logs",
        json={
            "readiness": 4,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_list_session_logs(
    authenticated_client: AsyncClient, test_user: User, test_program_with_workout: tuple, db_session: AsyncSession
):
    """Test GET /workouts/logs endpoint."""
    _, workout, _ = test_program_with_workout

    # Create multiple logs
    for i in range(3):
        data = UserWorkoutLogCreate(readiness=i + 1)
        await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)

    await db_session.commit()

    response = await authenticated_client.get("/api/v1/workouts/logs")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in log for log in data)


@pytest.mark.asyncio
async def test_endpoint_list_session_logs_pagination(
    authenticated_client: AsyncClient, test_user: User, test_program_with_workout: tuple, db_session: AsyncSession
):
    """Test pagination on GET /workouts/logs."""
    _, workout, _ = test_program_with_workout

    # Create 5 logs
    for i in range(5):
        data = UserWorkoutLogCreate(readiness=1)
        await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)

    await db_session.commit()

    # Test limit
    response = await authenticated_client.get("/api/v1/workouts/logs?limit=2&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Test offset
    response = await authenticated_client.get("/api/v1/workouts/logs?limit=2&offset=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_endpoint_append_set_log(authenticated_client: AsyncClient, test_program_with_workout: tuple):
    """Test POST /workouts/{id}/sets endpoint."""
    _, workout, exercise = test_program_with_workout

    response = await authenticated_client.post(
        f"/api/v1/workouts/{workout.id}/sets",
        json={
            "workout_id": workout.id,
            "workout_exercise_id": exercise.id,
            "set_number": 1,
            "actual_weight": 70.0,
            "actual_reps": 10,
            "actual_rpe": 8.0,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["set_number"] == 1
    assert data["actual_weight"] == 70.0
    assert data["actual_reps"] == 10
    assert data["actual_rpe"] == 8.0


@pytest.mark.asyncio
async def test_endpoint_append_set_log_unauthorized(client: AsyncClient, test_program_with_workout: tuple):
    """Test that unauthenticated set log requests are rejected."""
    _, workout, exercise = test_program_with_workout

    response = await client.post(
        f"/api/v1/workouts/{workout.id}/sets",
        json={
            "workout_id": workout.id,
            "workout_exercise_id": exercise.id,
            "set_number": 1,
            "actual_weight": 70.0,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_get_set_logs(
    authenticated_client: AsyncClient, test_user: User, test_program_with_workout: tuple, db_session: AsyncSession
):
    """Test GET /workouts/{id}/sets endpoint."""
    _, workout, exercise = test_program_with_workout

    # Add some set logs
    for i in range(3):
        data = WorkoutSetLogCreate(
            workout_id=workout.id,
            workout_exercise_id=exercise.id,
            set_number=i + 1,
            actual_weight=70.0 + i,
            actual_reps=10,
            actual_rpe=7.0,
        )
        await crud_logging.append_set_log(db_session, test_user.id, data)

    await db_session.commit()

    response = await authenticated_client.get(f"/api/v1/workouts/{workout.id}/sets")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_readiness_validation_rejected_zero():
    """Test that readiness=0 is rejected during validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserWorkoutLogCreate(readiness=0)


@pytest.mark.asyncio
async def test_readiness_validation_rejected_six():
    """Test that readiness=6 is rejected during validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserWorkoutLogCreate(readiness=6)


@pytest.mark.asyncio
async def test_readiness_validation_accepted_range():
    """Test that readiness 1-5 is accepted."""
    for readiness in range(1, 6):
        schema = UserWorkoutLogCreate(readiness=readiness)
        assert schema.readiness == readiness


@pytest.mark.asyncio
async def test_rpe_validation_rejected_zero():
    """Test that actual_rpe=0 is rejected during validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_rpe=0.0,
        )


@pytest.mark.asyncio
async def test_rpe_validation_rejected_eleven():
    """Test that actual_rpe=11 is rejected during validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_rpe=11.0,
        )


@pytest.mark.asyncio
async def test_rpe_validation_accepted_range():
    """Test that actual_rpe 1.0-10.0 is accepted."""
    for rpe in [1.0, 5.0, 10.0]:
        schema = WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_rpe=rpe,
        )
        assert schema.actual_rpe == rpe


@pytest.mark.asyncio
async def test_endpoint_get_session_log(
    authenticated_client: AsyncClient, test_user: User, test_program_with_workout: tuple, db_session: AsyncSession
):
    """Test GET /workouts/{id}/logs/{log_id} endpoint."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(readiness=3, notes="Test")
    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    response = await authenticated_client.get(f"/api/v1/workouts/{workout.id}/logs/{log.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log.id
    assert data["readiness"] == 3


@pytest.mark.asyncio
async def test_endpoint_get_session_log_not_found(authenticated_client: AsyncClient, test_program_with_workout: tuple):
    """Test 404 when session log not found."""
    _, workout, _ = test_program_with_workout

    response = await authenticated_client.get(f"/api/v1/workouts/{workout.id}/logs/9999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_endpoint_get_session_log_wrong_user(
    client: AsyncClient,
    other_user_headers: dict,
    test_user: User,
    test_program_with_workout: tuple,
    db_session: AsyncSession,
):
    """Test that users cannot access other users' session logs via endpoint."""
    _, workout, _ = test_program_with_workout

    data = UserWorkoutLogCreate(readiness=3)
    log = await crud_logging.create_workout_log(db_session, test_user.id, workout.id, data)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/workouts/{workout.id}/logs/{log.id}",
        headers=other_user_headers,
    )

    assert response.status_code == 404
