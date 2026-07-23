import pytest
from httpx import AsyncClient
from pydantic import ValidationError
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


class TestSetLogValidation:
    """Test WorkoutSetLogCreate field validation."""

    @pytest.mark.asyncio
    async def test_weight_validation_negative_rejected(self):
        """Test that negative weight is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_weight=-5.0,
            )
        assert "Weight must be >= 0" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_weight_validation_zero_accepted(self):
        """Test that weight=0 is accepted."""
        schema = WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_weight=0.0,
        )
        assert schema.actual_weight == 0.0

    @pytest.mark.asyncio
    async def test_weight_validation_positive_accepted(self):
        """Test that positive weight is accepted."""
        schema = WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_weight=75.5,
        )
        assert schema.actual_weight == 75.5

    @pytest.mark.asyncio
    async def test_weight_validation_none_accepted(self):
        """Test that None weight is accepted."""
        schema = WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_weight=None,
        )
        assert schema.actual_weight is None

    @pytest.mark.asyncio
    async def test_reps_validation_zero_rejected(self):
        """Test that reps=0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_reps=0,
            )
        assert "Reps must be between 1 and 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reps_validation_over_100_rejected(self):
        """Test that reps > 100 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_reps=101,
            )
        assert "Reps must be between 1 and 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reps_validation_range_accepted(self):
        """Test that reps 1-100 are accepted."""
        for reps in [1, 50, 100]:
            schema = WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_reps=reps,
            )
            assert schema.actual_reps == reps

    @pytest.mark.asyncio
    async def test_reps_validation_none_accepted(self):
        """Test that None reps is accepted."""
        schema = WorkoutSetLogCreate(
            workout_id=1,
            workout_exercise_id=1,
            set_number=1,
            actual_reps=None,
        )
        assert schema.actual_reps is None

    @pytest.mark.asyncio
    async def test_rpe_validation_zero_rejected(self):
        """Test that actual_rpe=0 is rejected."""
        with pytest.raises(ValidationError):
            WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_rpe=0.0,
            )

    @pytest.mark.asyncio
    async def test_rpe_validation_eleven_rejected(self):
        """Test that actual_rpe=11 is rejected."""
        with pytest.raises(ValidationError):
            WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_rpe=11.0,
            )

    @pytest.mark.asyncio
    async def test_rpe_validation_range_accepted(self):
        """Test that actual_rpe 1.0-10.0 is accepted."""
        for rpe in [1.0, 5.5, 10.0]:
            schema = WorkoutSetLogCreate(
                workout_id=1,
                workout_exercise_id=1,
                set_number=1,
                actual_rpe=rpe,
            )
            assert schema.actual_rpe == rpe


class TestReadinessValidation:
    """Test UserWorkoutLogCreate field validation."""

    @pytest.mark.asyncio
    async def test_readiness_validation_zero_rejected(self):
        """Test that readiness=0 is rejected."""
        with pytest.raises(ValidationError):
            UserWorkoutLogCreate(workout_id=1, readiness=0)

    @pytest.mark.asyncio
    async def test_readiness_validation_six_rejected(self):
        """Test that readiness=6 is rejected."""
        with pytest.raises(ValidationError):
            UserWorkoutLogCreate(workout_id=1, readiness=6)

    @pytest.mark.asyncio
    async def test_readiness_validation_range_accepted(self):
        """Test that readiness 1-5 is accepted."""
        for readiness in range(1, 6):
            schema = UserWorkoutLogCreate(workout_id=1, readiness=readiness)
            assert schema.readiness == readiness


class TestSetLogEndpoint:
    """Test POST /users/me/workouts/{workout_id}/set-logs endpoint."""

    @pytest.mark.asyncio
    async def test_create_set_log_success(self, authenticated_client: AsyncClient, test_program_with_workout: tuple):
        """Test creating a set log with valid data."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
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
        assert data["workout_id"] == workout.id
        assert data["workout_exercise_id"] == exercise.id
        assert data["set_number"] == 1
        assert data["actual_weight"] == 70.0
        assert data["actual_reps"] == 10
        assert data["actual_rpe"] == 8.0

    @pytest.mark.asyncio
    async def test_create_set_log_unauthorized(self, client: AsyncClient, test_program_with_workout: tuple):
        """Test that unauthenticated requests are rejected."""
        _, workout, exercise = test_program_with_workout

        response = await client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_weight": 70.0,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_set_log_workout_id_mismatch(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that workout_id mismatch is rejected."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": 999,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_weight": 70.0,
            },
        )

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_set_log_workout_not_found(self, authenticated_client: AsyncClient):
        """Test 404 when workout not found."""
        response = await authenticated_client.post(
            "/api/v1/users/me/workouts/9999/set-logs",
            json={
                "workout_id": 9999,
                "workout_exercise_id": 1,
                "set_number": 1,
                "actual_weight": 70.0,
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_set_log_other_user_workout(
        self,
        client: AsyncClient,
        other_user_headers: dict,
        test_program_with_workout: tuple,
    ):
        """Test that users cannot create logs for other users' workouts."""
        _, workout, exercise = test_program_with_workout

        response = await client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            headers=other_user_headers,
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_weight": 70.0,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_set_log_with_none_values(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test creating a set log with optional None values."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_weight": None,
                "actual_reps": None,
                "actual_rpe": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["actual_weight"] is None
        assert data["actual_reps"] is None
        assert data["actual_rpe"] is None

    @pytest.mark.asyncio
    async def test_create_set_log_invalid_weight(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that negative weight is rejected."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_weight": -10.0,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_set_log_invalid_reps(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that reps > 100 is rejected."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_reps": 101,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_set_log_invalid_rpe(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that RPE > 10 is rejected."""
        _, workout, exercise = test_program_with_workout

        response = await authenticated_client.post(
            f"/api/v1/users/me/workouts/{workout.id}/set-logs",
            json={
                "workout_id": workout.id,
                "workout_exercise_id": exercise.id,
                "set_number": 1,
                "actual_rpe": 11.0,
            },
        )

        assert response.status_code == 422


class TestReadinessEndpoint:
    """Test PATCH /users/me/workouts/{workout_id}/readiness endpoint."""

    @pytest.mark.asyncio
    async def test_update_readiness_create_new(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test creating a new readiness log."""
        _, workout, _ = test_program_with_workout

        response = await authenticated_client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": workout.id,
                "readiness": 4,
                "notes": "Feeling good",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["workout_id"] == workout.id
        assert data["readiness"] == 4
        assert data["notes"] == "Feeling good"

    @pytest.mark.asyncio
    async def test_update_readiness_update_existing(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_program_with_workout: tuple,
        db_session: AsyncSession,
    ):
        """Test updating existing readiness log."""
        _, workout, _ = test_program_with_workout

        data = UserWorkoutLogCreate(workout_id=workout.id, readiness=2, notes="Original")
        original_log = await crud_logging.create_workout_log(db_session, test_user.id, data)
        await db_session.commit()

        response = await authenticated_client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": workout.id,
                "readiness": 5,
                "notes": "Updated",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == original_log.id
        assert data["readiness"] == 5
        assert data["notes"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_readiness_unauthorized(self, client: AsyncClient, test_program_with_workout: tuple):
        """Test that unauthenticated requests are rejected."""
        _, workout, _ = test_program_with_workout

        response = await client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": workout.id,
                "readiness": 4,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_readiness_workout_id_mismatch(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that workout_id mismatch is rejected."""
        _, workout, _ = test_program_with_workout

        response = await authenticated_client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": 999,
                "readiness": 4,
            },
        )

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_readiness_workout_not_found(self, authenticated_client: AsyncClient):
        """Test 404 when workout not found."""
        response = await authenticated_client.patch(
            "/api/v1/users/me/workouts/9999/readiness",
            json={
                "workout_id": 9999,
                "readiness": 4,
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_readiness_other_user_workout(
        self,
        client: AsyncClient,
        other_user_headers: dict,
        test_program_with_workout: tuple,
    ):
        """Test that users cannot update readiness for other users' workouts."""
        _, workout, _ = test_program_with_workout

        response = await client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            headers=other_user_headers,
            json={
                "workout_id": workout.id,
                "readiness": 4,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_readiness_invalid_value(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test that invalid readiness values are rejected."""
        _, workout, _ = test_program_with_workout

        response = await authenticated_client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": workout.id,
                "readiness": 6,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_readiness_with_notes(
        self, authenticated_client: AsyncClient, test_program_with_workout: tuple
    ):
        """Test updating readiness with notes."""
        _, workout, _ = test_program_with_workout

        response = await authenticated_client.patch(
            f"/api/v1/users/me/workouts/{workout.id}/readiness",
            json={
                "workout_id": workout.id,
                "readiness": 3,
                "notes": "Slight soreness",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["readiness"] == 3
        assert data["notes"] == "Slight soreness"
