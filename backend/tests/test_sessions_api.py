from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.models import ProgramStatus, User, Workout, WorkoutProgram
from app.services.auth import create_tokens
from app.services.program.scheduling import materialize_sessions


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


@pytest_asyncio.fixture
async def active_program(db_session: AsyncSession, test_user: User, seeded_templates: None) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=1,
        environment_id=1,
        name="Test Program",
        status=ProgramStatus.ACTIVE,
        duration_weeks=4,
        days_per_week=3,
        start_date=date.today(),
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()
    for order, key in enumerate(["a", "b", "c"]):
        db_session.add(Workout(program_id=program.id, key=key, name=f"Day {key.upper()}", order=order))
    await db_session.commit()
    await db_session.refresh(program, ["workouts"])
    await materialize_sessions(db_session, program)
    return program


@pytest.mark.asyncio
async def test_schedule_returns_sessions_in_the_window(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    _end = date.today().replace(day=28).isoformat() if date.today().day < 28 else start

    response = await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["scheduled_date"] == start
    assert body[0]["status"] == "scheduled"
    assert body[0]["week"] == 1


@pytest.mark.asyncio
async def test_schedule_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me/schedule?start=2026-07-27&end=2026-07-31")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_session_detail_includes_the_week_resolved_slots(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    listed = await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")
    session_id = listed.json()[0]["session_id"]

    response = await authenticated_client.get(f"/api/v1/users/me/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["program_id"] == active_program.id
    assert "slots" in body
    assert body["logged_sets"] == []


@pytest.mark.asyncio
async def test_session_detail_404s_for_a_stranger(
    client: AsyncClient, active_program: WorkoutProgram, other_user_token: str
) -> None:
    client.cookies.set("access_token", other_user_token)

    response = await client.get("/api/v1/users/me/sessions/1")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_detail_slots_come_from_the_sessions_own_week(
    authenticated_client: AsyncClient, db_session: AsyncSession, seeded_templates, seeded_exercises, user_environment
) -> None:
    draft = await authenticated_client.post(
        "/api/v1/programs/draft",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "general_fitness",
            "weight_unit": "kg",
            "duration_weeks": 4,
            "template_id": 1,
            "required_inputs": {"squat_start": 60.0, "bench_start": 40.0},
            "progression_style": "consistent",
            "effort_method": "rpe",
            "start_date": date.today().isoformat(),
        },
    )
    program_id = draft.json()["program_id"]
    await authenticated_client.post(f"/api/v1/programs/{program_id}/accept")

    schedule = await authenticated_client.get(
        f"/api/v1/users/me/schedule?start={date.today().isoformat()}&end=2027-01-01"
    )
    entries = schedule.json()
    week_1 = next(e for e in entries if e["week"] == 1)
    week_4 = next(e for e in entries if e["week"] == 4 and e["workout_id"] == week_1["workout_id"])

    detail_1 = (await authenticated_client.get(f"/api/v1/users/me/sessions/{week_1['session_id']}")).json()
    detail_4 = (await authenticated_client.get(f"/api/v1/users/me/sessions/{week_4['session_id']}")).json()

    assert len(detail_1["slots"]) > 0
    assert len(detail_4["slots"]) == len(detail_1["slots"])
    assert detail_1["slots"][0]["workout_exercise_id"] == detail_4["slots"][0]["workout_exercise_id"]
    # Same template slot, different week: linear progression must move the load.
    assert detail_1["slots"][0]["load"] != detail_4["slots"][0]["load"]


@pytest.mark.asyncio
async def test_first_set_log_moves_the_session_to_in_progress(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0][
        "session_id"
    ]

    response = await authenticated_client.post(
        f"/api/v1/users/me/sessions/{session_id}/set-logs",
        json={"workout_exercise_id": 1, "set_number": 1, "actual_reps": 8, "actual_rpe": 8.0},
    )

    assert response.status_code == 201
    assert response.json()["session_id"] == session_id

    detail = await authenticated_client.get(f"/api/v1/users/me/sessions/{session_id}")
    assert detail.json()["status"] == "in_progress"
    assert len(detail.json()["logged_sets"]) == 1


@pytest.mark.asyncio
async def test_completing_a_session_marks_it_completed(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0][
        "session_id"
    ]

    response = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_completing_twice_is_idempotent(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0][
        "session_id"
    ]

    first = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")
    second = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")

    assert second.status_code == 200
    assert second.json()["completed_at"] == first.json()["completed_at"]


@pytest.mark.asyncio
async def test_readiness_is_recorded_against_the_sessions_workout(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    entry = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0]

    response = await authenticated_client.post(
        f"/api/v1/users/me/sessions/{entry['session_id']}/readiness",
        json={"readiness": 4, "phase": "pre"},
    )

    assert response.status_code == 201
    assert response.json()["workout_id"] == entry["workout_id"]


@pytest.mark.asyncio
async def test_writes_404_for_a_stranger(
    client: AsyncClient, active_program: WorkoutProgram, other_user_token: str
) -> None:
    client.cookies.set("access_token", other_user_token)

    response = await client.post("/api/v1/users/me/sessions/1/complete")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_set_log_is_always_anchored_to_its_session(
    authenticated_client: AsyncClient, active_program: WorkoutProgram, db_session: AsyncSession
) -> None:
    start = date.today().isoformat()
    entry = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0]

    await authenticated_client.post(
        f"/api/v1/users/me/sessions/{entry['session_id']}/set-logs",
        json={"workout_exercise_id": 1, "set_number": 1, "actual_reps": 8, "actual_rpe": 8.0},
    )

    from app.models import WorkoutSetLog

    logs = (await db_session.execute(select(WorkoutSetLog))).scalars().all()
    assert [log.session_id for log in logs] == [entry["session_id"]]
    assert [log.workout_id for log in logs] == [entry["workout_id"]]
