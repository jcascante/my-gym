# Workout Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give MyGym a real workout schedule — materialized session rows with dates and status — so users can browse past, present, and upcoming sessions instead of being dropped straight into the exercise logger.

**Architecture:** A new `workout_sessions` table holds one row per (program, week, workout template) with a `scheduled_date` and `status`. Sessions are materialized when a program is accepted (DRAFT → ACTIVE). A lazy flip marks past `scheduled` rows `missed` on read. The frontend gains a `/schedule` week browser and a `/sessions/:id` detail screen ahead of the existing logger.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest/pytest-asyncio. React 18, TypeScript, TanStack Query, react-router-dom, Tailwind, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-07-27-workout-schedule-design.md`

## Global Constraints

- All I/O is `async`/`await`. No sync DB calls.
- Strict mypy on `backend/app/`, TypeScript strict on frontend.
- TDD: write the failing test, watch it fail, implement, watch it pass, commit.
- Backend commands run through Docker: `docker-compose exec backend <cmd>`. Same for frontend.
- REST under `/api/v1/`. Auth via `Depends(get_current_user)`; every session endpoint is ownership-scoped through `WorkoutProgram.user_id`.
- Set logs stay append-only. Nothing in this plan updates or deletes a `WorkoutSetLog`.
- Comments only for non-obvious *why*. No comments restating what the code does, and no references to tasks, PRs, or plan step numbers in committed code.
- Current Alembic head is `9f1a2b3c4d5e`. The one new migration in this plan descends from it.
- Dates compare against server-side `date.today()`. Per-user timezones are out of scope.
- Out of scope, do not build: user-editable training days, a `skipped` UI action, backfilling existing ACTIVE programs.

---

## File Structure

**Backend — created**

| File | Responsibility |
| --- | --- |
| `backend/app/models/session.py` | `WorkoutSession` ORM model + `SessionStatus` enum |
| `backend/app/schemas/session.py` | Pydantic in/out schemas for schedule and session detail |
| `backend/app/services/program/scheduling.py` | Offset table, date arithmetic, materialization |
| `backend/app/services/program/loading.py` | Shared program + template-definition loader (extracted from `programs.py:_load`) |
| `backend/app/crud/session.py` | Session queries: by range, by id, status transitions |
| `backend/app/api/v1/endpoints/sessions.py` | The five session endpoints |
| `backend/alembic/versions/<rev>_add_workout_sessions.py` | Schema-only migration |
| `backend/tests/test_scheduling.py` | Offset table + date arithmetic + materialization |
| `backend/tests/test_sessions_api.py` | Endpoint behaviour, ownership, status transitions |

**Backend — modified**

| File | Change |
| --- | --- |
| `backend/app/models/__init__.py` | Export `WorkoutSession`, `SessionStatus` |
| `backend/app/models/logging.py` | `WorkoutSetLog.session_id` nullable FK |
| `backend/app/schemas/logging.py` | `WorkoutSetLogOut.session_id` |
| `backend/app/crud/logging.py` | `append_set_log` persists `session_id` |
| `backend/app/api/v1/endpoints/programs.py` | `accept` materializes sessions; `_load` delegates to the extracted loader; `start_date` on the preview |
| `backend/app/schemas/program_api.py` | `ProgramPreviewOut.start_date` |
| `backend/app/crud/session.py` | Session queries and the missed-flip |
| `backend/app/main.py` | Register the sessions router |

**Frontend — created**

| File | Responsibility |
| --- | --- |
| `frontend/src/types/session.ts` | `SessionStatus`, `ScheduleEntry`, `SessionDetail` |
| `frontend/src/api/sessions.ts` | Five API functions |
| `frontend/src/hooks/useSchedule.ts` | `useSchedule`, `useTodaySession` |
| `frontend/src/hooks/useSession.ts` | `useSession` |
| `frontend/src/hooks/useSessionProgress.ts` | Per-exercise set progress state, lifted out of the tracking page |
| `frontend/src/components/SessionStatusBadge.tsx` | Status pill |
| `frontend/src/components/ScheduleRow.tsx` | One row in the week list |
| `frontend/src/pages/SchedulePage.tsx` | Week browser |
| `frontend/src/pages/SessionDetailPage.tsx` | Status-aware session detail |
| Tests mirroring each of the above under `frontend/src/tests/` | |

**Frontend — modified**

| File | Change |
| --- | --- |
| `frontend/src/App.tsx` | Route changes |
| `frontend/src/components/Header.tsx` | Schedule nav entry |
| `frontend/src/components/index.ts` | Export new components |
| `frontend/src/pages/DashboardPage.tsx` | Drive the card from `useTodaySession` |
| `frontend/src/pages/WorkoutTrackingPage.tsx` | Session-driven; use `useSessionProgress`; fix the `/dashboard` navigate |
| `frontend/src/api/logging.ts` | Session-scoped set-log path |
| `frontend/src/api/workouts.ts` | Session-scoped readiness path |

**Frontend — deleted**

`frontend/src/hooks/useWorkoutDetails.ts` and `frontend/src/tests/hooks/useWorkoutDetails.test.tsx` (Task 12).

---

# Phase 1 — Backend

## Task 1: WorkoutSession model and migration

**Files:**
- Create: `backend/app/models/session.py`
- Create: `backend/alembic/versions/a3f81c9d2e40_add_workout_sessions.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/logging.py:44-55`
- Test: `backend/tests/test_session_model.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.models.session.SessionStatus` — a `str, enum.Enum` with members `SCHEDULED = "scheduled"`, `IN_PROGRESS = "in_progress"`, `COMPLETED = "completed"`, `MISSED = "missed"`, `SKIPPED = "skipped"`.
  - `app.models.session.WorkoutSession` — columns `id: int`, `program_id: int`, `workout_id: int`, `week: int`, `scheduled_date: date`, `status: SessionStatus`, `completed_at: datetime | None`, `created_at: datetime`, `updated_at: datetime`.
  - `app.models.logging.WorkoutSetLog.session_id: int | None`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_session_model.py`:

```python
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, WorkoutSession


@pytest.mark.asyncio
async def test_session_defaults_to_scheduled(db_session: AsyncSession) -> None:
    session = WorkoutSession(
        program_id=1, workout_id=1, week=1, scheduled_date=date(2026, 7, 27)
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.status == SessionStatus.SCHEDULED
    assert session.completed_at is None


@pytest.mark.asyncio
async def test_program_workout_week_is_unique(db_session: AsyncSession) -> None:
    for _ in range(2):
        db_session.add(
            WorkoutSession(
                program_id=1, workout_id=1, week=1, scheduled_date=date(2026, 7, 27)
            )
        )

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_set_log_carries_a_session_id(db_session: AsyncSession) -> None:
    from app.models import WorkoutSetLog

    log = WorkoutSetLog(
        user_id=1, workout_id=1, workout_exercise_id=1, set_number=1, session_id=7
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.session_id == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_session_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'SessionStatus' from 'app.models'`

- [ ] **Step 3: Write the model**

Create `backend/app/models/session.py`:

```python
import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import _utcnow


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    SKIPPED = "skipped"


class WorkoutSession(Base):
    """One dated occurrence of a workout template within a program week.

    Workout rows are templates re-rendered per week by derive_week, so workout_id
    alone never identifies a session - (program_id, workout_id, week) does.
    """

    __tablename__ = "workout_sessions"
    __table_args__ = (UniqueConstraint("program_id", "workout_id", "week", name="uq_session_program_workout_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("workout_programs.id"), nullable=False, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False, default=SessionStatus.SCHEDULED)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
```

- [ ] **Step 4: Add the set-log column**

In `backend/app/models/logging.py`, inside `WorkoutSetLog`, add after the `workout_exercise_id` column:

```python
    session_id: Mapped[int | None] = mapped_column(ForeignKey("workout_sessions.id"), index=True)
```

- [ ] **Step 5: Export from the models package**

In `backend/app/models/__init__.py`, add the import next to the other model imports:

```python
from .session import SessionStatus, WorkoutSession
```

and add `"SessionStatus"` and `"WorkoutSession"` to `__all__`.

- [ ] **Step 6: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_session_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Write the migration**

Create `backend/alembic/versions/a3f81c9d2e40_add_workout_sessions.py`:

```python
"""add workout_sessions

Revision ID: a3f81c9d2e40
Revises: 9f1a2b3c4d5e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f81c9d2e40"
down_revision: Union[str, None] = "9f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SESSION_STATUS = sa.Enum(
    "SCHEDULED", "IN_PROGRESS", "COMPLETED", "MISSED", "SKIPPED", name="sessionstatus"
)


def upgrade() -> None:
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", SESSION_STATUS, nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["workout_programs.id"]),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "workout_id", "week", name="uq_session_program_workout_week"),
    )
    op.create_index(op.f("ix_workout_sessions_program_id"), "workout_sessions", ["program_id"])
    op.create_index(op.f("ix_workout_sessions_workout_id"), "workout_sessions", ["workout_id"])
    op.create_index(op.f("ix_workout_sessions_scheduled_date"), "workout_sessions", ["scheduled_date"])

    op.add_column("workout_set_logs", sa.Column("session_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_workout_set_logs_session_id"), "workout_set_logs", ["session_id"])
    op.create_foreign_key(
        "fk_workout_set_logs_session_id", "workout_set_logs", "workout_sessions", ["session_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_workout_set_logs_session_id", "workout_set_logs", type_="foreignkey")
    op.drop_index(op.f("ix_workout_set_logs_session_id"), table_name="workout_set_logs")
    op.drop_column("workout_set_logs", "session_id")

    op.drop_index(op.f("ix_workout_sessions_scheduled_date"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_workout_id"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_program_id"), table_name="workout_sessions")
    op.drop_table("workout_sessions")
    SESSION_STATUS.drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 8: Verify the migration round-trips**

Run:
```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```
Expected: all three succeed with no error. `alembic heads` reports exactly one head, `a3f81c9d2e40`.

- [ ] **Step 9: Type check and commit**

```bash
docker-compose exec backend mypy app/
git add backend/app/models/session.py backend/app/models/__init__.py backend/app/models/logging.py backend/alembic/versions/a3f81c9d2e40_add_workout_sessions.py backend/tests/test_session_model.py
git commit -m "feat(sessions): add WorkoutSession model and migration"
```

---

## Task 2: Schedule date arithmetic

**Files:**
- Create: `backend/app/services/program/scheduling.py`
- Test: `backend/tests/test_scheduling.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `weekday_offsets(n: int) -> list[int]` — evenly spread day offsets for `n` sessions per week. Raises `ValueError` outside 1..7.
  - `session_date(start_date: date, week: int, index: int, offsets: list[int]) -> date`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_scheduling.py`:

```python
from datetime import date

import pytest

from app.services.program.scheduling import session_date, weekday_offsets


@pytest.mark.parametrize(
    "days,expected",
    [
        (1, [0]),
        (2, [0, 3]),
        (3, [0, 2, 4]),
        (4, [0, 1, 3, 4]),
        (5, [0, 1, 2, 3, 4]),
        (6, [0, 1, 2, 3, 4, 5]),
        (7, [0, 1, 2, 3, 4, 5, 6]),
    ],
)
def test_weekday_offsets(days: int, expected: list[int]) -> None:
    assert weekday_offsets(days) == expected


@pytest.mark.parametrize("days", [0, 8, -1])
def test_weekday_offsets_rejects_out_of_range(days: int) -> None:
    with pytest.raises(ValueError):
        weekday_offsets(days)


def test_session_date_first_session_is_the_start_date() -> None:
    offsets = weekday_offsets(3)
    assert session_date(date(2026, 7, 27), 1, 0, offsets) == date(2026, 7, 27)


def test_session_date_spreads_within_the_first_week() -> None:
    offsets = weekday_offsets(3)
    start = date(2026, 7, 27)  # a Monday
    assert session_date(start, 1, 1, offsets) == date(2026, 7, 29)
    assert session_date(start, 1, 2, offsets) == date(2026, 7, 31)


def test_session_date_advances_seven_days_per_week() -> None:
    offsets = weekday_offsets(3)
    start = date(2026, 7, 27)
    assert session_date(start, 3, 0, offsets) == date(2026, 8, 10)


def test_session_date_crosses_a_month_boundary() -> None:
    offsets = weekday_offsets(4)
    start = date(2026, 7, 27)
    assert session_date(start, 2, 3, offsets) == date(2026, 8, 7)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.program.scheduling'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/program/scheduling.py`:

```python
from datetime import date, timedelta

# Day offsets from the program's start weekday, spread to leave rest days where
# the week allows it. Keyed by sessions per week.
_OFFSETS: dict[int, list[int]] = {
    1: [0],
    2: [0, 3],
    3: [0, 2, 4],
    4: [0, 1, 3, 4],
    5: [0, 1, 2, 3, 4],
    6: [0, 1, 2, 3, 4, 5],
    7: [0, 1, 2, 3, 4, 5, 6],
}


def weekday_offsets(sessions_per_week: int) -> list[int]:
    if sessions_per_week not in _OFFSETS:
        raise ValueError(f"sessions_per_week must be 1-7, got {sessions_per_week}")
    return list(_OFFSETS[sessions_per_week])


def session_date(start_date: date, week: int, index: int, offsets: list[int]) -> date:
    return start_date + timedelta(days=(week - 1) * 7 + offsets[index])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/scheduling.py backend/tests/test_scheduling.py
git commit -m "feat(sessions): add schedule date arithmetic"
```

---

## Task 3: Materialize sessions on program activation

**Files:**
- Modify: `backend/app/services/program/scheduling.py`
- Modify: `backend/app/api/v1/endpoints/programs.py:396-404`
- Test: `backend/tests/test_scheduling.py`

**Interfaces:**
- Consumes: `weekday_offsets`, `session_date` (Task 2); `WorkoutSession`, `SessionStatus` (Task 1).
- Produces: `async def materialize_sessions(db: AsyncSession, program: WorkoutProgram) -> list[WorkoutSession]` — inserts one session per (week, workout), writes the resolved offsets to `program.constraints["training_day_offsets"]`, and returns the created rows. Returns `[]` and inserts nothing when the program has no `start_date`, no workouts, or already has sessions.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_scheduling.py`:

```python
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramStatus, SessionStatus, Workout, WorkoutProgram, WorkoutSession
from app.services.program.scheduling import materialize_sessions


@pytest_asyncio.fixture
async def three_day_program(db_session: AsyncSession) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Test Program",
        status=ProgramStatus.DRAFT,
        duration_weeks=4,
        days_per_week=3,
        start_date=date(2026, 7, 27),
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()
    for order, key in enumerate(["a", "b", "c"]):
        db_session.add(Workout(program_id=program.id, key=key, name=f"Day {key.upper()}", order=order))
    await db_session.commit()
    await db_session.refresh(program, ["workouts"])
    return program


@pytest.mark.asyncio
async def test_materialize_creates_a_row_per_week_and_workout(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    created = await materialize_sessions(db_session, three_day_program)

    assert len(created) == 12
    assert {s.status for s in created} == {SessionStatus.SCHEDULED}
    assert {s.week for s in created} == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_materialize_dates_follow_the_offset_table(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    result = await db_session.execute(
        select(WorkoutSession).where(WorkoutSession.week == 1).order_by(WorkoutSession.scheduled_date)
    )
    dates = [s.scheduled_date for s in result.scalars().all()]

    assert dates == [date(2026, 7, 27), date(2026, 7, 29), date(2026, 7, 31)]


@pytest.mark.asyncio
async def test_materialize_records_the_offsets_on_the_program(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    assert three_day_program.constraints["training_day_offsets"] == [0, 2, 4]


@pytest.mark.asyncio
async def test_materialize_is_idempotent(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)
    second = await materialize_sessions(db_session, three_day_program)

    assert second == []
    result = await db_session.execute(select(WorkoutSession))
    assert len(list(result.scalars().all())) == 12


@pytest.mark.asyncio
async def test_materialize_skips_a_program_without_a_start_date(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    three_day_program.start_date = None

    assert await materialize_sessions(db_session, three_day_program) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v -k materialize`
Expected: FAIL — `ImportError: cannot import name 'materialize_sessions'`

- [ ] **Step 3: Write the implementation**

Append to `backend/app/services/program/scheduling.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.program import WorkoutProgram
from app.models.session import SessionStatus, WorkoutSession


async def materialize_sessions(db: AsyncSession, program: WorkoutProgram) -> list[WorkoutSession]:
    """Create the dated session rows for a program, once."""
    if program.start_date is None or not program.workouts:
        return []

    existing = await db.execute(select(WorkoutSession.id).where(WorkoutSession.program_id == program.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return []

    workouts = sorted(program.workouts, key=lambda w: w.order)
    offsets = weekday_offsets(len(workouts))

    # Pinned so the dates stay put even if the spread table is later changed.
    program.constraints["training_day_offsets"] = offsets
    flag_modified(program, "constraints")

    sessions = [
        WorkoutSession(
            program_id=program.id,
            workout_id=workout.id,
            week=week,
            scheduled_date=session_date(program.start_date, week, index, offsets),
            status=SessionStatus.SCHEDULED,
        )
        for week in range(1, program.duration_weeks + 1)
        for index, workout in enumerate(workouts)
    ]
    db.add_all(sessions)
    await db.commit()
    return sessions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v`
Expected: PASS (19 tests)

- [ ] **Step 5: Wire it into program acceptance**

In `backend/app/api/v1/endpoints/programs.py`, add to the imports:

```python
from app.services.program.scheduling import materialize_sessions
```

and change the `accept` endpoint body (currently lines 396-404) to:

```python
@router.post("/{program_id}/accept", response_model=ProgramPreviewOut)
async def accept(
    program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProgramPreviewOut:
    program, definition = await _load(db, user, program_id)
    program.status = ProgramStatus.ACTIVE
    await save_program(db, program)
    await materialize_sessions(db, program)
    program = cast(WorkoutProgram, await get_program(db, user.id, program_id))
    return await _preview_out(db, program, definition, user)
```

- [ ] **Step 6: Write the acceptance test**

Append to `backend/tests/test_scheduling.py`:

```python
@pytest.mark.asyncio
async def test_accepting_a_program_materializes_its_sessions(
    authenticated_client, db_session: AsyncSession, seeded_templates, seeded_exercises, user_environment
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
            "required_inputs": {},
            "progression_style": "linear",
            "effort_method": "rpe",
            "start_date": "2026-07-27",
        },
    )
    program_id = draft.json()["program_id"]

    response = await authenticated_client.post(f"/api/v1/programs/{program_id}/accept")
    assert response.status_code == 200

    result = await db_session.execute(
        select(WorkoutSession).where(WorkoutSession.program_id == program_id)
    )
    sessions = list(result.scalars().all())
    assert len(sessions) == 12
    assert min(s.scheduled_date for s in sessions) == date(2026, 7, 27)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker-compose exec backend pytest tests/test_scheduling.py tests/test_programs_flow.py -v`
Expected: PASS. If the draft payload above is rejected, read the request schema in `backend/app/schemas/program_api.py` and the existing draft calls in `backend/tests/test_programs_flow.py`, and align the fixture payload — do not change the endpoint.

- [ ] **Step 8: Commit**

```bash
docker-compose exec backend mypy app/ && docker-compose exec backend ruff check . --fix
git add backend/app/services/program/scheduling.py backend/app/api/v1/endpoints/programs.py backend/tests/test_scheduling.py
git commit -m "feat(sessions): materialize sessions when a program is accepted"
```

---

## Task 4: The lazy missed-flip

**Files:**
- Create: `backend/app/crud/session.py`
- Test: `backend/tests/test_scheduling.py`

**Interfaces:**
- Consumes: `WorkoutSession`, `SessionStatus` (Task 1).
- Produces: `async def flip_missed(db: AsyncSession, program_id: int, today: date) -> None` — sets `status = MISSED` on every `SCHEDULED` row of that program dated before `today`. Touches nothing in any other status.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_scheduling.py`:

```python
from app.crud.session import flip_missed


@pytest.mark.asyncio
async def test_flip_marks_past_scheduled_sessions_missed(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    result = await db_session.execute(
        select(WorkoutSession).where(WorkoutSession.program_id == three_day_program.id)
    )
    by_date = {s.scheduled_date: s.status for s in result.scalars().all()}

    assert by_date[date(2026, 7, 27)] == SessionStatus.MISSED
    assert by_date[date(2026, 7, 29)] == SessionStatus.MISSED
    assert by_date[date(2026, 7, 31)] == SessionStatus.SCHEDULED


@pytest.mark.asyncio
async def test_flip_leaves_an_abandoned_in_progress_session_alone(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)
    abandoned = next(s for s in sessions if s.scheduled_date == date(2026, 7, 27))
    abandoned.status = SessionStatus.IN_PROGRESS
    await db_session.commit()

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    await db_session.refresh(abandoned)
    assert abandoned.status == SessionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_flip_leaves_completed_sessions_alone(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)
    done = next(s for s in sessions if s.scheduled_date == date(2026, 7, 27))
    done.status = SessionStatus.COMPLETED
    await db_session.commit()

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 30))

    await db_session.refresh(done)
    assert done.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_flip_does_not_touch_todays_session(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    await flip_missed(db_session, three_day_program.id, date(2026, 7, 27))

    result = await db_session.execute(
        select(WorkoutSession).where(WorkoutSession.program_id == three_day_program.id)
    )
    assert {s.status for s in result.scalars().all()} == {SessionStatus.SCHEDULED}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v -k flip`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.crud.session'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/crud/session.py`:

```python
from datetime import date

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionStatus, WorkoutSession


async def flip_missed(db: AsyncSession, program_id: int, today: date) -> None:
    """Age out past sessions the user never started.

    Only SCHEDULED rows move, so a session left IN_PROGRESS stays that way
    rather than being reported as never attempted.
    """
    await db.execute(
        update(WorkoutSession)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                WorkoutSession.status == SessionStatus.SCHEDULED,
                WorkoutSession.scheduled_date < today,
            )
        )
        .values(status=SessionStatus.MISSED)
    )
    await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v`
Expected: PASS (24 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/crud/session.py backend/tests/test_scheduling.py
git commit -m "feat(sessions): flip past scheduled sessions to missed"
```

---

## Task 5: Session queries

**Files:**
- Modify: `backend/app/crud/session.py`
- Test: `backend/tests/test_scheduling.py`

**Interfaces:**
- Consumes: `flip_missed` (Task 4).
- Produces:
  - `async def get_sessions_in_range(db, user_id: int, start: date, end: date) -> list[WorkoutSession]` — the user's sessions with `start <= scheduled_date <= end`, ordered by date, flipping missed rows first.
  - `async def get_session(db, session_id: int, user_id: int) -> WorkoutSession | None` — ownership-scoped, flipping missed rows for that program first.
  - `async def set_session_status(db, session: WorkoutSession, status: SessionStatus) -> WorkoutSession` — writes `completed_at` when moving to `COMPLETED`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_scheduling.py`:

```python
from app.crud.session import get_session, get_sessions_in_range, set_session_status


@pytest.mark.asyncio
async def test_range_query_returns_only_sessions_in_the_window(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    three_day_program.user_id = 1
    await materialize_sessions(db_session, three_day_program)

    found = await get_sessions_in_range(db_session, 1, date(2026, 7, 27), date(2026, 8, 2))

    assert [s.scheduled_date for s in found] == [
        date(2026, 7, 27),
        date(2026, 7, 29),
        date(2026, 7, 31),
    ]


@pytest.mark.asyncio
async def test_range_query_excludes_another_users_sessions(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    await materialize_sessions(db_session, three_day_program)

    assert await get_sessions_in_range(db_session, 999, date(2026, 1, 1), date(2027, 1, 1)) == []


@pytest.mark.asyncio
async def test_get_session_is_scoped_to_the_owner(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)

    assert await get_session(db_session, sessions[0].id, 1) is not None
    assert await get_session(db_session, sessions[0].id, 999) is None


@pytest.mark.asyncio
async def test_completing_a_session_stamps_completed_at(
    db_session: AsyncSession, three_day_program: WorkoutProgram
) -> None:
    sessions = await materialize_sessions(db_session, three_day_program)

    updated = await set_session_status(db_session, sessions[0], SessionStatus.COMPLETED)

    assert updated.status == SessionStatus.COMPLETED
    assert updated.completed_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v -k "range_query or get_session or completing"`
Expected: FAIL — `ImportError: cannot import name 'get_sessions_in_range'`

- [ ] **Step 3: Write the implementation**

Append to `backend/app/crud/session.py`:

```python
from sqlalchemy import select

from app.models.program import WorkoutProgram
from app.models.user import _utcnow


async def get_sessions_in_range(
    db: AsyncSession, user_id: int, start: date, end: date
) -> list[WorkoutSession]:
    program_ids = (
        await db.execute(select(WorkoutProgram.id).where(WorkoutProgram.user_id == user_id))
    ).scalars().all()
    if not program_ids:
        return []

    for program_id in program_ids:
        await flip_missed(db, program_id, date.today())

    result = await db.execute(
        select(WorkoutSession)
        .where(
            and_(
                WorkoutSession.program_id.in_(program_ids),
                WorkoutSession.scheduled_date >= start,
                WorkoutSession.scheduled_date <= end,
            )
        )
        .order_by(WorkoutSession.scheduled_date, WorkoutSession.id)
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: int, user_id: int) -> WorkoutSession | None:
    result = await db.execute(
        select(WorkoutSession)
        .join(WorkoutProgram, WorkoutProgram.id == WorkoutSession.program_id)
        .where(and_(WorkoutSession.id == session_id, WorkoutProgram.user_id == user_id))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    await flip_missed(db, session.program_id, date.today())
    await db.refresh(session)
    return session


async def set_session_status(
    db: AsyncSession, session: WorkoutSession, status: SessionStatus
) -> WorkoutSession:
    session.status = status
    if status == SessionStatus.COMPLETED:
        session.completed_at = _utcnow()
    await db.commit()
    await db.refresh(session)
    return session
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_scheduling.py -v`
Expected: PASS (28 tests)

- [ ] **Step 5: Commit**

```bash
docker-compose exec backend mypy app/
git add backend/app/crud/session.py backend/tests/test_scheduling.py
git commit -m "feat(sessions): add session range and detail queries"
```

---

## Task 6: Session schemas

**Files:**
- Create: `backend/app/schemas/session.py`
- Modify: `backend/app/schemas/logging.py:67-82`
- Test: `backend/tests/test_session_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ScheduleEntryOut` — `session_id: int`, `scheduled_date: date`, `week: int`, `status: str`, `workout_id: int`, `workout_name: str`, `exercise_count: int`, `duration_min: int`.
  - `SessionDetailOut` — everything in `ScheduleEntryOut` plus `program_id: int`, `program_name: str`, `slots: list[SlotPreviewOut]`, `logged_sets: list[WorkoutSetLogOut]`, `reactive_deload: bool`, `deload_reason: str | None`.
  - `SessionSetLogCreate` — `workout_exercise_id: int`, `set_number: int`, `actual_weight: float | None`, `actual_reps: int | None`, `actual_rpe: float | None`, `effort_method: Literal["rpe", "rir", "borg"]`. No `workout_id`; the session supplies it.
  - `WorkoutSetLogOut.session_id: int | None`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_session_schemas.py`:

```python
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.session import ScheduleEntryOut, SessionSetLogCreate


def test_schedule_entry_round_trips() -> None:
    entry = ScheduleEntryOut(
        session_id=1,
        scheduled_date=date(2026, 7, 27),
        week=1,
        status="scheduled",
        workout_id=4,
        workout_name="Upper Body A",
        exercise_count=5,
        duration_min=45,
    )

    assert entry.model_dump()["scheduled_date"] == date(2026, 7, 27)


def test_session_set_log_does_not_take_a_workout_id() -> None:
    log = SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_reps=8, actual_rpe=8.0)

    assert "workout_id" not in log.model_dump()


def test_session_set_log_rejects_a_bad_rpe() -> None:
    with pytest.raises(ValidationError):
        SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_rpe=99.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_session_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.session'`

- [ ] **Step 3: Write the schemas**

Create `backend/app/schemas/session.py`:

```python
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.schemas.logging import WorkoutSetLogOut
from app.schemas.program_api import SlotPreviewOut


class ScheduleEntryOut(BaseModel):
    """One dated session as it appears in the schedule list."""

    session_id: int
    scheduled_date: date
    week: int
    status: str
    workout_id: int
    workout_name: str
    exercise_count: int
    duration_min: int


class SessionDetailOut(ScheduleEntryOut):
    """A session with its week-resolved prescription and any logged sets."""

    program_id: int
    program_name: str
    slots: list[SlotPreviewOut]
    logged_sets: list[WorkoutSetLogOut]
    reactive_deload: bool
    deload_reason: Optional[str]


class SessionSetLogCreate(BaseModel):
    """Append a set to a session. The session supplies the workout."""

    workout_exercise_id: int
    set_number: int = Field(ge=1)
    actual_weight: Optional[float] = None
    actual_reps: Optional[int] = None
    effort_method: Literal["rpe", "rir", "borg"] = "rpe"
    actual_rpe: Optional[float] = None

    @field_validator("actual_weight")
    @classmethod
    def validate_weight(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Weight must be >= 0")
        return v

    @field_validator("actual_reps")
    @classmethod
    def validate_reps(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 100):
            raise ValueError("Reps must be between 1 and 100")
        return v

    @field_validator("actual_rpe")
    @classmethod
    def validate_effort_value(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        if v is None:
            return v
        effort_method = info.data.get("effort_method", "rpe")
        if effort_method == "rpe" and not (1.0 <= v <= 10.0):
            raise ValueError("RPE must be 1-10")
        if effort_method == "rir" and not (0.0 <= v <= 10.0):
            raise ValueError("RIR must be 0-10")
        if effort_method == "borg" and not (6.0 <= v <= 20.0):
            raise ValueError("Borg scale must be 6-20")
        return v
```

- [ ] **Step 4: Add session_id to the set-log output schema**

In `backend/app/schemas/logging.py`, add to `WorkoutSetLogOut` after `workout_exercise_id`:

```python
    session_id: Optional[int] = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_session_schemas.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
docker-compose exec backend mypy app/
git add backend/app/schemas/session.py backend/app/schemas/logging.py backend/tests/test_session_schemas.py
git commit -m "feat(sessions): add session request and response schemas"
```

---

## Task 7: GET /schedule and GET /sessions/{id}

**Files:**
- Create: `backend/app/api/v1/endpoints/sessions.py`
- Modify: `backend/app/main.py:94`
- Test: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `get_sessions_in_range`, `get_session` (Task 5); `ScheduleEntryOut`, `SessionDetailOut` (Task 6).
- Produces: `sessions_router` — an `APIRouter(prefix="/users/me", tags=["sessions"])` exporting `GET /schedule` and `GET /sessions/{session_id}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_sessions_api.py`:

```python
from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramStatus, User, Workout, WorkoutProgram
from app.services.program.scheduling import materialize_sessions


@pytest_asyncio.fixture
async def active_program(db_session: AsyncSession, test_user: User) -> WorkoutProgram:
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
    end = date.today().replace(day=28).isoformat() if date.today().day < 28 else start

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
```

Copy the `other_user` / `other_user_token` fixtures from `backend/tests/test_logging.py:14-38` into this file.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v`
Expected: FAIL — 404 on every route; the router does not exist yet.

- [ ] **Step 3: Write the endpoints**

Create `backend/app/api/v1/endpoints/sessions.py`:

```python
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.crud.session import get_session, get_sessions_in_range
from app.models.program import Workout, WorkoutProgram
from app.models.session import WorkoutSession
from app.models.user import User
from app.schemas.session import ScheduleEntryOut, SessionDetailOut

router = APIRouter(prefix="/users/me", tags=["sessions"])

DEFAULT_DURATION_MIN = 45


async def _workout_for(db: AsyncSession, session: WorkoutSession) -> Workout:
    result = await db.execute(select(Workout).where(Workout.id == session.workout_id))
    workout = result.scalar_one_or_none()
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


def _duration_for(user: User) -> int:
    # get_user_by_id selectinloads User.profile, so this never lazy-loads.
    return (user.profile.workout_duration_min if user.profile else None) or DEFAULT_DURATION_MIN


@router.get("/schedule", response_model=list[ScheduleEntryOut])
async def list_schedule(
    start: date,
    end: date,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduleEntryOut]:
    sessions = await get_sessions_in_range(db, user.id, start, end)
    duration_min = _duration_for(user)

    entries = []
    for session in sessions:
        workout = await _workout_for(db, session)
        entries.append(
            ScheduleEntryOut(
                session_id=session.id,
                scheduled_date=session.scheduled_date,
                week=session.week,
                status=session.status.value,
                workout_id=workout.id,
                workout_name=workout.name,
                exercise_count=len(workout.exercises),
                duration_min=duration_min,
            )
        )
    return entries


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
async def get_session_detail(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailOut:
    session = await get_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    workout = await _workout_for(db, session)
    program = (
        await db.execute(select(WorkoutProgram).where(WorkoutProgram.id == session.program_id))
    ).scalar_one()

    return SessionDetailOut(
        session_id=session.id,
        scheduled_date=session.scheduled_date,
        week=session.week,
        status=session.status.value,
        workout_id=workout.id,
        workout_name=workout.name,
        exercise_count=len(workout.exercises),
        duration_min=_duration_for(user),
        program_id=program.id,
        program_name=program.name,
        slots=[],
        logged_sets=[],
        reactive_deload=False,
        deload_reason=None,
    )
```

`slots` and `logged_sets` are filled in by Task 8. Leaving them empty here keeps this task's tests honest about what is actually wired.

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, add the import alongside the other endpoint imports:

```python
from app.api.v1.endpoints.sessions import router as sessions_router
```

and after line 94:

```python
app.include_router(sessions_router, prefix=settings.API_V1_STR)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
docker-compose exec backend mypy app/ && docker-compose exec backend ruff check . --fix
git add backend/app/api/v1/endpoints/sessions.py backend/app/main.py backend/tests/test_sessions_api.py
git commit -m "feat(sessions): add schedule and session detail endpoints"
```

---

## Task 8: Fill session detail with slots and logged sets

**Files:**
- Create: `backend/app/services/program/loading.py`
- Modify: `backend/app/api/v1/endpoints/programs.py:293-300`
- Modify: `backend/app/api/v1/endpoints/sessions.py`
- Test: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `derive_week` from `app.services.program.preview`.
- Produces:
  - `app.services.program.loading.load_program_with_definition(db, user_id: int, program_id: int) -> tuple[WorkoutProgram, TemplateDefinition]` — the body currently inlined in `programs.py:_load`, made importable. Raises `ProgramNotFoundError`.
  - `SessionDetailOut.slots` populated from `derive_week(program, definition, session.week)`, and `logged_sets` from the session's set logs.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_sessions_api.py`:

```python
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
            "required_inputs": {},
            "progression_style": "linear",
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v -k own_week`
Expected: FAIL — `assert len([]) > 0`, because `slots` is hardcoded empty.

- [ ] **Step 3: Extract the program+definition loader**

`programs.py:_load` already resolves a program into a `(WorkoutProgram, TemplateDefinition)` pair with the progression style applied. Sessions need the same pair, so move it somewhere both can import.

Create `backend/app/services/program/loading.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ProgramNotFoundError
from app.crud.program import get_program, get_template
from app.models.program import WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.style_override import apply_progression_style


async def load_program_with_definition(
    db: AsyncSession, user_id: int, program_id: int
) -> tuple[WorkoutProgram, TemplateDefinition]:
    program = await get_program(db, user_id, program_id)
    if program is None:
        raise ProgramNotFoundError()
    template = await get_template(db, program.template_id)
    definition = TemplateDefinition.from_orm_template(template)
    style = program.constraints.get("progression_style", "consistent")
    return program, apply_progression_style(definition, style)
```

Then reduce `programs.py:_load` (lines 293-300) to a delegation so its fourteen call sites stay untouched:

```python
async def _load(db: AsyncSession, user: User, program_id: int) -> tuple[WorkoutProgram, TemplateDefinition]:
    return await load_program_with_definition(db, user.id, program_id)
```

adding `from app.services.program.loading import load_program_with_definition` to its imports. If `ProgramNotFoundError` is not importable from `app.core`, take the import path `programs.py` already uses for it.

Run `docker-compose exec backend pytest tests/test_programs_flow.py -v` and confirm it still passes before continuing.

- [ ] **Step 4: Populate slots and logged sets**

In `backend/app/api/v1/endpoints/sessions.py`, add imports:

```python
from app.models.logging import WorkoutSetLog
from app.schemas.logging import WorkoutSetLogOut
from app.schemas.program_api import WorkoutPreviewOut
from app.services.program.loading import load_program_with_definition
from app.services.program.preview import derive_week
```

Replace the `program = (await db.execute(select(WorkoutProgram)...)).scalar_one()` line and the `return SessionDetailOut(...)` block in `get_session_detail` with:

```python
    program, definition = await load_program_with_definition(db, user.id, session.program_id)
    week_days = derive_week(program, definition, session.week)
    day = next((d for d in week_days if d["workout_id"] == session.workout_id), None)
    preview = WorkoutPreviewOut(**day) if day else None

    logs = (
        await db.execute(
            select(WorkoutSetLog)
            .where(WorkoutSetLog.session_id == session.id)
            .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
        )
    ).scalars().all()

    return SessionDetailOut(
        session_id=session.id,
        scheduled_date=session.scheduled_date,
        week=session.week,
        status=session.status.value,
        workout_id=workout.id,
        workout_name=workout.name,
        exercise_count=len(workout.exercises),
        duration_min=_duration_for(user),
        program_id=program.id,
        program_name=program.name,
        slots=preview.slots if preview else [],
        logged_sets=[WorkoutSetLogOut.model_validate(log) for log in logs],
        reactive_deload=preview.reactive_deload if preview else False,
        deload_reason=preview.deload_reason if preview else None,
    )
```

`load_program_with_definition` wraps `get_program`, which eager-loads workouts and their exercises — `derive_week` walks `program.workouts[*].exercises`, so the bare `select(WorkoutProgram)` from Task 7 would lazy-load and fail.

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
docker-compose exec backend mypy app/ && docker-compose exec backend ruff check . --fix
git add backend/app/services/program/loading.py backend/app/api/v1/endpoints/programs.py backend/app/api/v1/endpoints/sessions.py backend/tests/test_sessions_api.py
git commit -m "feat(sessions): resolve session slots from the session's own week"
```

---

## Task 9: Session write endpoints

**Files:**
- Modify: `backend/app/api/v1/endpoints/sessions.py`
- Modify: `backend/app/crud/logging.py:52-67`
- Test: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `set_session_status` (Task 5); `SessionSetLogCreate` (Task 6).
- Produces: `POST /users/me/sessions/{session_id}/set-logs`, `POST /users/me/sessions/{session_id}/readiness`, `POST /users/me/sessions/{session_id}/complete`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_sessions_api.py`:

```python
@pytest.mark.asyncio
async def test_first_set_log_moves_the_session_to_in_progress(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (
        await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")
    ).json()[0]["session_id"]

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
    session_id = (
        await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")
    ).json()[0]["session_id"]

    response = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_completing_twice_is_idempotent(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (
        await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")
    ).json()[0]["session_id"]

    first = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")
    second = await authenticated_client.post(f"/api/v1/users/me/sessions/{session_id}/complete")

    assert second.status_code == 200
    assert second.json()["completed_at"] == first.json()["completed_at"]


@pytest.mark.asyncio
async def test_readiness_is_recorded_against_the_sessions_workout(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    entry = (
        await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")
    ).json()[0]

    response = await authenticated_client.post(
        f"/api/v1/users/me/sessions/{entry['session_id']}/readiness",
        json={"readiness": 4, "phase": "pre"},
    )

    assert response.status_code == 201
    assert response.json()["workout_id"] == entry["workout_id"]


@pytest.mark.asyncio
async def test_writes_404_for_a_stranger(client: AsyncClient, active_program: WorkoutProgram, other_user_token: str) -> None:
    client.cookies.set("access_token", other_user_token)

    response = await client.post("/api/v1/users/me/sessions/1/complete")

    assert response.status_code == 404
```

`test_completing_twice_is_idempotent` requires `completed_at` on the response, so add `completed_at: Optional[datetime] = None` to `SessionDetailOut` in `backend/app/schemas/session.py` and populate it from `session.completed_at`.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v -k "set_log or completing or readiness or stranger"`
Expected: FAIL — 405 or 404; the write routes do not exist.

- [ ] **Step 3: Persist session_id on set logs**

In `backend/app/crud/logging.py`, change `append_set_log` to accept and store the session:

```python
async def append_set_log(
    db: AsyncSession, user_id: int, data: WorkoutSetLogCreate, session_id: int | None = None
) -> WorkoutSetLog:
    """Append a new set log to a workout session."""
    log = WorkoutSetLog(
        user_id=user_id,
        workout_id=data.workout_id,
        workout_exercise_id=data.workout_exercise_id,
        set_number=data.set_number,
        actual_weight=data.actual_weight,
        actual_reps=data.actual_reps,
        actual_rpe=data.actual_rpe,
        effort_method=data.effort_method,
        session_id=session_id,
    )
    db.add(log)
    await db.flush()
    await db.commit()
    await db.refresh(log)
    return log
```

The default keeps the existing `/workouts/{id}/set-logs` callers working unchanged.

- [ ] **Step 4: Write the endpoints**

Append to `backend/app/api/v1/endpoints/sessions.py`:

```python
from app.crud import logging as crud_logging
from app.crud.session import set_session_status
from app.models.logging import UserWorkoutLog
from app.models.session import SessionStatus
from app.schemas.logging import UserWorkoutLogCreate, UserWorkoutLogOut, WorkoutSetLogCreate
from app.schemas.session import SessionSetLogCreate


async def _owned_session(db: AsyncSession, session_id: int, user: User) -> WorkoutSession:
    session = await get_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post(
    "/sessions/{session_id}/set-logs",
    response_model=WorkoutSetLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_set_log(
    session_id: int,
    data: SessionSetLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSetLog:
    session = await _owned_session(db, session_id, user)

    log = await crud_logging.append_set_log(
        db,
        user.id,
        WorkoutSetLogCreate(workout_id=session.workout_id, **data.model_dump()),
        session_id=session.id,
    )

    if session.status == SessionStatus.SCHEDULED:
        await set_session_status(db, session, SessionStatus.IN_PROGRESS)

    return log


@router.post(
    "/sessions/{session_id}/readiness",
    response_model=UserWorkoutLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_readiness(
    session_id: int,
    data: UserWorkoutLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkoutLog:
    session = await _owned_session(db, session_id, user)
    return await crud_logging.create_workout_log(db, user.id, session.workout_id, data)


@router.post("/sessions/{session_id}/complete", response_model=SessionDetailOut)
async def complete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailOut:
    session = await _owned_session(db, session_id, user)

    if session.status != SessionStatus.COMPLETED:
        await set_session_status(db, session, SessionStatus.COMPLETED)

    return await get_session_detail(session_id, user, db)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_sessions_api.py -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Run the full backend suite**

Run: `docker-compose exec backend pytest`
Expected: PASS, with no regressions in `test_logging.py` or `test_programs_flow.py`.

- [ ] **Step 7: Commit**

```bash
docker-compose exec backend mypy app/ && docker-compose exec backend ruff check . --fix && docker-compose exec backend black .
git add backend/app/api/v1/endpoints/sessions.py backend/app/crud/logging.py backend/app/schemas/session.py backend/tests/test_sessions_api.py
git commit -m "feat(sessions): add set-log, readiness, and complete endpoints"
```

---

# Phase 2 — Frontend

## Task 10: Session types and API client

**Files:**
- Create: `frontend/src/types/session.ts`
- Create: `frontend/src/api/sessions.ts`
- Test: `frontend/src/tests/api/sessions.test.ts`

**Interfaces:**
- Consumes: the Phase 1 endpoints.
- Produces:
  - `SessionStatus = 'scheduled' | 'in_progress' | 'completed' | 'missed' | 'skipped'`
  - `ScheduleEntry`, `SessionDetail`, `SessionSetLogPayload` (fields mirror the Task 6 schemas)
  - `getSchedule(start: string, end: string): Promise<ScheduleEntry[]>`
  - `getSession(sessionId: number): Promise<SessionDetail>`
  - `logSessionSet(sessionId: number, payload: SessionSetLogPayload): Promise<void>`
  - `postSessionReadiness(sessionId: number, readiness: number, phase?: 'pre' | 'post'): Promise<void>`
  - `completeSession(sessionId: number): Promise<SessionDetail>`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/api/sessions.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getSchedule, getSession, logSessionSet, completeSession } from '@/api/sessions';
import { apiClient } from '@/api/client';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

describe('sessions api', () => {
  beforeEach(() => vi.clearAllMocks());

  it('requests the schedule for a date range', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await getSchedule('2026-07-27', '2026-08-02');

    expect(apiClient.get).toHaveBeenCalledWith('/users/me/schedule', {
      params: { start: '2026-07-27', end: '2026-08-02' },
    });
  });

  it('requests a single session by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { session_id: 5 } });

    const result = await getSession(5);

    expect(apiClient.get).toHaveBeenCalledWith('/users/me/sessions/5');
    expect(result.session_id).toBe(5);
  });

  it('posts a set log to the session, not the workout', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });

    await logSessionSet(5, { workout_exercise_id: 3, set_number: 1, actual_reps: 8 });

    expect(apiClient.post).toHaveBeenCalledWith('/users/me/sessions/5/set-logs', {
      workout_exercise_id: 3,
      set_number: 1,
      actual_reps: 8,
    });
  });

  it('completes a session', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { status: 'completed' } });

    const result = await completeSession(5);

    expect(apiClient.post).toHaveBeenCalledWith('/users/me/sessions/5/complete');
    expect(result.status).toBe('completed');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/api/sessions.test.ts`
Expected: FAIL — cannot resolve `@/api/sessions`

- [ ] **Step 3: Write the types**

Create `frontend/src/types/session.ts`:

```typescript
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';

export type SessionStatus = 'scheduled' | 'in_progress' | 'completed' | 'missed' | 'skipped';

export interface ScheduleEntry {
  session_id: number;
  scheduled_date: string;
  week: number;
  status: SessionStatus;
  workout_id: number;
  workout_name: string;
  exercise_count: number;
  duration_min: number;
}

export interface LoggedSet {
  id: number;
  workout_exercise_id: number;
  set_number: number;
  actual_weight: number | null;
  actual_reps: number | null;
  actual_rpe: number | null;
  effort_method: string;
}

export interface SessionDetail extends ScheduleEntry {
  program_id: number;
  program_name: string;
  slots: SlotPreview[];
  logged_sets: LoggedSet[];
  completed_at: string | null;
  reactive_deload: boolean;
  deload_reason: string | null;
}

export interface SessionSetLogPayload {
  workout_exercise_id: number;
  set_number: number;
  actual_weight?: number;
  actual_reps?: number;
  actual_rpe?: number;
  effort_method?: EffortMethod;
}
```

- [ ] **Step 4: Write the API client**

Create `frontend/src/api/sessions.ts`:

```typescript
import { apiClient } from '@/api/client';
import type { ScheduleEntry, SessionDetail, SessionSetLogPayload } from '@/types/session';

export async function getSchedule(start: string, end: string): Promise<ScheduleEntry[]> {
  const { data } = await apiClient.get<ScheduleEntry[]>('/users/me/schedule', {
    params: { start, end },
  });
  return data;
}

export async function getSession(sessionId: number): Promise<SessionDetail> {
  const { data } = await apiClient.get<SessionDetail>(`/users/me/sessions/${sessionId}`);
  return data;
}

export async function logSessionSet(
  sessionId: number,
  payload: SessionSetLogPayload,
): Promise<void> {
  await apiClient.post(`/users/me/sessions/${sessionId}/set-logs`, payload);
}

export async function postSessionReadiness(
  sessionId: number,
  readiness: number,
  phase?: 'pre' | 'post',
): Promise<void> {
  await apiClient.post(`/users/me/sessions/${sessionId}/readiness`, {
    readiness,
    ...(phase && { phase }),
  });
}

export async function completeSession(sessionId: number): Promise<SessionDetail> {
  const { data } = await apiClient.post<SessionDetail>(`/users/me/sessions/${sessionId}/complete`);
  return data;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- src/tests/api/sessions.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
docker-compose exec frontend npm run type-check
git add frontend/src/types/session.ts frontend/src/api/sessions.ts frontend/src/tests/api/sessions.test.ts
git commit -m "feat(sessions): add session types and API client"
```

---

## Task 11: Schedule and session hooks

**Files:**
- Create: `frontend/src/hooks/useSchedule.ts`
- Create: `frontend/src/hooks/useSession.ts`
- Test: `frontend/src/tests/hooks/useSchedule.test.tsx`

**Interfaces:**
- Consumes: `getSchedule`, `getSession` (Task 10).
- Produces:
  - `sessionKeys = { schedule: (start, end) => [...], detail: (id) => [...] }`
  - `useSchedule(start: string, end: string)` — TanStack Query result of `ScheduleEntry[]`.
  - `useTodaySession()` — `{ session: ScheduleEntry | null, isLoading: boolean }` for today's date.
  - `useSession(sessionId: number | null)` — TanStack Query result of `SessionDetail`, disabled when null.
  - `weekRange(startDate: string, week: number): { start: string; end: string }` — the ISO date bounds of a program week.
  - `toIsoDate(d: Date): string`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/hooks/useSchedule.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSchedule, useTodaySession, toIsoDate } from '@/hooks/useSchedule';
import { getSchedule } from '@/api/sessions';

vi.mock('@/api/sessions', () => ({ getSchedule: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const entry = {
  session_id: 1,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('useSchedule', () => {
  beforeEach(() => vi.clearAllMocks());

  it('formats a Date as an ISO day string', () => {
    expect(toIsoDate(new Date(2026, 6, 27))).toBe('2026-07-27');
  });

  it('fetches the given range', async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);

    const { result } = renderHook(() => useSchedule('2026-07-27', '2026-08-02'), { wrapper });

    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(getSchedule).toHaveBeenCalledWith('2026-07-27', '2026-08-02');
  });

  it('returns null when today has no session', async () => {
    vi.mocked(getSchedule).mockResolvedValue([]);

    const { result } = renderHook(() => useTodaySession(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.session).toBeNull();
  });

  it("returns today's session when one exists", async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);

    const { result } = renderHook(() => useTodaySession(), { wrapper });

    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.session?.session_id).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/hooks/useSchedule.test.tsx`
Expected: FAIL — cannot resolve `@/hooks/useSchedule`

- [ ] **Step 3: Write the hooks**

Create `frontend/src/hooks/useSchedule.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { getSchedule } from '@/api/sessions';
import type { ScheduleEntry } from '@/types/session';

export const sessionKeys = {
  schedule: (start: string, end: string) => ['schedule', start, end] as const,
  detail: (id: number) => ['session', id] as const,
};

export function toIsoDate(d: Date): string {
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

export function weekRange(startDate: string, week: number): { start: string; end: string } {
  const [y, m, d] = startDate.split('-').map(Number);
  const start = new Date(y, m - 1, d + (week - 1) * 7);
  const end = new Date(y, m - 1, d + (week - 1) * 7 + 6);
  return { start: toIsoDate(start), end: toIsoDate(end) };
}

export function useSchedule(start: string, end: string) {
  return useQuery({
    queryKey: sessionKeys.schedule(start, end),
    queryFn: () => getSchedule(start, end),
  });
}

export function useTodaySession(): { session: ScheduleEntry | null; isLoading: boolean } {
  const today = toIsoDate(new Date());
  const { data, isLoading } = useSchedule(today, today);
  return { session: data?.[0] ?? null, isLoading };
}
```

Create `frontend/src/hooks/useSession.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { getSession } from '@/api/sessions';
import { sessionKeys } from '@/hooks/useSchedule';

export function useSession(sessionId: number | null) {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId ?? 0),
    queryFn: () => getSession(sessionId as number),
    enabled: sessionId !== null,
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- src/tests/hooks/useSchedule.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
docker-compose exec frontend npm run type-check
git add frontend/src/hooks/useSchedule.ts frontend/src/hooks/useSession.ts frontend/src/tests/hooks/useSchedule.test.tsx
git commit -m "feat(sessions): add schedule and session query hooks"
```

---

## Task 12: SessionStatusBadge and ScheduleRow

**Files:**
- Create: `frontend/src/components/SessionStatusBadge.tsx`
- Create: `frontend/src/components/ScheduleRow.tsx`
- Modify: `frontend/src/components/index.ts`
- Test: `frontend/src/tests/components/ScheduleRow.test.tsx`

**Interfaces:**
- Consumes: `ScheduleEntry`, `SessionStatus` (Task 10).
- Produces:
  - `displayStatus(status: SessionStatus, scheduledDate: string, today: string): 'done' | 'today' | 'upcoming' | 'missed' | 'in progress' | 'skipped'` — exported from `SessionStatusBadge.tsx`.
  - `SessionStatusBadgeProps { status: SessionStatus; scheduledDate: string; today: string }` — all three required.
  - `ScheduleRowProps { entry: ScheduleEntry; today: string; onSelect: (sessionId: number) => void }`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/components/ScheduleRow.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScheduleRow } from '@/components/ScheduleRow';
import { displayStatus } from '@/components/SessionStatusBadge';
import type { ScheduleEntry } from '@/types/session';

const entry: ScheduleEntry = {
  session_id: 1,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled',
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('displayStatus', () => {
  it('reads a scheduled session dated today as today', () => {
    expect(displayStatus('scheduled', '2026-07-27', '2026-07-27')).toBe('today');
  });

  it('reads a scheduled session dated later as upcoming', () => {
    expect(displayStatus('scheduled', '2026-07-31', '2026-07-27')).toBe('upcoming');
  });

  it('reads a completed session as done regardless of date', () => {
    expect(displayStatus('completed', '2026-07-20', '2026-07-27')).toBe('done');
  });

  it('reads a missed session as missed', () => {
    expect(displayStatus('missed', '2026-07-20', '2026-07-27')).toBe('missed');
  });
});

describe('ScheduleRow', () => {
  it('shows the weekday, name, and status', () => {
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={vi.fn()} />);

    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
    expect(screen.getByText(/Mon/)).toBeInTheDocument();
    expect(screen.getByText('today')).toBeInTheDocument();
  });

  it('calls onSelect with the session id when clicked', async () => {
    const onSelect = vi.fn();
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/components/ScheduleRow.test.tsx`
Expected: FAIL — cannot resolve `@/components/ScheduleRow`

- [ ] **Step 3: Write SessionStatusBadge**

Create `frontend/src/components/SessionStatusBadge.tsx`:

```typescript
import type { SessionStatus } from '@/types/session';

export type DisplayStatus = 'done' | 'today' | 'upcoming' | 'missed' | 'in progress' | 'skipped';

// 'today' and 'upcoming' are not stored: both are scheduled rows, split by date.
export function displayStatus(
  status: SessionStatus,
  scheduledDate: string,
  today: string,
): DisplayStatus {
  if (status === 'completed') return 'done';
  if (status === 'missed') return 'missed';
  if (status === 'skipped') return 'skipped';
  if (status === 'in_progress') return 'in progress';
  return scheduledDate === today ? 'today' : 'upcoming';
}

const STYLES: Record<DisplayStatus, string> = {
  done: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200',
  today: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
  upcoming: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200',
  missed: 'bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200',
  'in progress': 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
  skipped: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200',
};

export interface SessionStatusBadgeProps {
  status: SessionStatus;
  scheduledDate: string;
  today: string;
}

export function SessionStatusBadge({ status, scheduledDate, today }: SessionStatusBadgeProps) {
  const display = displayStatus(status, scheduledDate, today);
  return (
    <span className={`label-sm px-2 py-1 rounded-full whitespace-nowrap ${STYLES[display]}`}>
      {display}
    </span>
  );
}
```

Confirm `success-*`, `error-*`, and `warning-*` exist in `frontend/tailwind.config.js`. If a scale is missing, substitute the nearest one that is defined rather than inventing a class.

- [ ] **Step 4: Write ScheduleRow**

Create `frontend/src/components/ScheduleRow.tsx`:

```typescript
import type { ScheduleEntry } from '@/types/session';
import { SessionStatusBadge } from '@/components/SessionStatusBadge';

export interface ScheduleRowProps {
  entry: ScheduleEntry;
  today: string;
  onSelect: (sessionId: number) => void;
}

export function ScheduleRow({ entry, today, onSelect }: ScheduleRowProps) {
  const [y, m, d] = entry.scheduled_date.split('-').map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    day: 'numeric',
  });

  return (
    <button
      type="button"
      onClick={() => onSelect(entry.session_id)}
      className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <span className="flex items-baseline gap-4 min-w-0">
        <span className="label-sm text-neutral-600 dark:text-neutral-400 w-16 shrink-0">
          {label}
        </span>
        <span className="body-md text-neutral-900 dark:text-neutral-50 truncate">
          {entry.workout_name}
        </span>
      </span>
      <SessionStatusBadge
        status={entry.status}
        scheduledDate={entry.scheduled_date}
        today={today}
      />
    </button>
  );
}
```

- [ ] **Step 5: Export both components**

In `frontend/src/components/index.ts`, append:

```typescript
export { SessionStatusBadge } from './SessionStatusBadge';
export { ScheduleRow } from './ScheduleRow';
```

- [ ] **Step 6: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- src/tests/components/ScheduleRow.test.tsx`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
docker-compose exec frontend npm run lint -- --fix && docker-compose exec frontend npm run type-check
git add frontend/src/components/SessionStatusBadge.tsx frontend/src/components/ScheduleRow.tsx frontend/src/components/index.ts frontend/src/tests/components/ScheduleRow.test.tsx
git commit -m "feat(sessions): add schedule row and status badge"
```

---

## Task 13: SchedulePage

**Files:**
- Create: `frontend/src/pages/SchedulePage.tsx`
- Modify: `frontend/src/App.tsx:65`
- Modify: `frontend/src/components/Header.tsx:60-66`
- Test: `frontend/src/tests/pages/SchedulePage.test.tsx`

**Interfaces:**
- Consumes: `useSchedule`, `weekRange`, `toIsoDate` (Task 11); `useActiveProgram` from `@/hooks/usePrograms`; `ScheduleRow` (Task 12).
- Produces: the `/schedule` route.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/pages/SchedulePage.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SchedulePage from '@/pages/SchedulePage';

const navigateMock = vi.fn();
let scheduleData: unknown[] = [];
let programData: unknown = null;

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('@/hooks/useSchedule', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useSchedule')>('@/hooks/useSchedule');
  return { ...actual, useSchedule: () => ({ data: scheduleData, isLoading: false }) };
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const entry = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('SchedulePage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    scheduleData = [entry];
    programData = {
      program_id: 1,
      name: 'My Program',
      status: 'active',
      duration_weeks: 8,
      current_week: 1,
      start_date: '2026-07-27',
      weeks: {},
      advisories: [],
    };
  });

  it('shows the current week and its sessions', () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Week 1 of 8/)).toBeInTheDocument();
    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
  });

  it('advances to the next week', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /next week/i }));

    expect(screen.getByText(/Week 2 of 8/)).toBeInTheDocument();
  });

  it('cannot go before week 1', () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /previous week/i })).toBeDisabled();
  });

  it('navigates to the session detail on select', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByText('Upper Body A'));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
  });

  it('explains an empty week for a program with no sessions', () => {
    scheduleData = [];

    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no sessions/i)).toBeInTheDocument();
  });

  it('links to program creation when there is no active program', () => {
    programData = null;

    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /create program/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/SchedulePage.test.tsx`
Expected: FAIL — cannot resolve `@/pages/SchedulePage`

- [ ] **Step 3: Write the page**

Create `frontend/src/pages/SchedulePage.tsx`:

```typescript
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useActiveProgram } from '@/hooks/usePrograms';
import { useSchedule, weekRange, toIsoDate } from '@/hooks/useSchedule';
import { Button, Card, ScheduleRow, Spinner } from '@/components';

export default function SchedulePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: program, isLoading: programLoading } = useActiveProgram();

  const initialWeek = Number(searchParams.get('week')) || program?.current_week || 1;
  const [week, setWeek] = useState(initialWeek);

  const startDate = program?.start_date ?? toIsoDate(new Date());
  const { start, end } = weekRange(startDate, week);
  const { data: sessions, isLoading } = useSchedule(start, end);

  const today = toIsoDate(new Date());
  const durationWeeks = program?.duration_weeks ?? 1;

  const goToWeek = (next: number) => {
    setWeek(next);
    setSearchParams({ week: String(next) });
  };

  if (programLoading) return <Spinner />;

  if (!program) {
    return (
      <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <Card padding="lg">
            <h1 className="heading-lg mb-2">No active program</h1>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create a program to see your training schedule.
            </p>
            <Button variant="primary" onClick={() => navigate('/programs/new')}>
              Create Program
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="display-md mb-6">Schedule</h1>

        <Card padding="md">
          <div className="flex items-center justify-between mb-4">
            <Button
              variant="secondary"
              aria-label="Previous week"
              disabled={week <= 1}
              onClick={() => goToWeek(week - 1)}
            >
              ←
            </Button>
            <p className="heading-md">
              Week {week} of {durationWeeks}
            </p>
            <Button
              variant="secondary"
              aria-label="Next week"
              disabled={week >= durationWeeks}
              onClick={() => goToWeek(week + 1)}
            >
              →
            </Button>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner size="sm" />
            </div>
          ) : sessions && sessions.length > 0 ? (
            <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
              {sessions.map((entry) => (
                <ScheduleRow
                  key={entry.session_id}
                  entry={entry}
                  today={today}
                  onSelect={(id) => navigate(`/sessions/${id}`)}
                />
              ))}
            </div>
          ) : (
            <p className="body-md text-neutral-600 dark:text-neutral-400 py-8 text-center">
              No sessions in this week. Programs activated before scheduling was added need to be
              re-activated to generate their schedule.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
```

`ProgramPreview` does not currently expose `start_date`. Add `start_date?: string | null` to the `ProgramPreview` interface in `frontend/src/types/program.ts`, and add `start_date=program.start_date` to `ProgramPreviewOut` in `backend/app/schemas/program_api.py` and `_preview_out` in `backend/app/api/v1/endpoints/programs.py`. Add a backend assertion for it in `backend/tests/test_sessions_api.py`.

- [ ] **Step 4: Add the route**

In `frontend/src/App.tsx`, import the page and add inside the authenticated block:

```typescript
<Route path="/schedule" element={<SchedulePage />} />
```

- [ ] **Step 5: Add the header nav entry**

In `frontend/src/components/Header.tsx`, add a Schedule button beside the logo button (around line 66), inside the same flex container:

```typescript
<button
  onClick={() => navigate('/schedule')}
  className="hidden sm:block px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
>
  Schedule
</button>
```

Wrap it and the logo button in a `<div className="flex items-center gap-2">` so the header's `justify-between` still puts the user menu on the right.

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/SchedulePage.test.tsx`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
docker-compose exec frontend npm run lint -- --fix && docker-compose exec frontend npm run type-check
git add frontend/src/pages/SchedulePage.tsx frontend/src/App.tsx frontend/src/components/Header.tsx frontend/src/types/program.ts frontend/src/tests/pages/SchedulePage.test.tsx backend/app/schemas/program_api.py backend/app/api/v1/endpoints/programs.py backend/tests/test_sessions_api.py
git commit -m "feat(sessions): add the schedule page"
```

---

## Task 14: SessionDetailPage

**Files:**
- Create: `frontend/src/pages/SessionDetailPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/tests/pages/SessionDetailPage.test.tsx`

**Interfaces:**
- Consumes: `useSession` (Task 11); `SessionDetail` (Task 10).
- Produces: the `/sessions/:sessionId` route.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/pages/SessionDetailPage.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SessionDetailPage from '@/pages/SessionDetailPage';

const navigateMock = vi.fn();
let sessionData: unknown;

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({ data: sessionData, isLoading: false, error: null }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ sessionId: '9' }) };
});

const slot = {
  workout_exercise_id: 3,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 4,
  reps: 8,
  load: 80,
  rest_seconds: 120,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
};

const base = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 3,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 1,
  duration_min: 45,
  program_id: 1,
  program_name: 'My Program',
  slots: [slot],
  logged_sets: [],
  completed_at: null,
  reactive_deload: false,
  deload_reason: null,
};

describe('SessionDetailPage', () => {
  beforeEach(() => navigateMock.mockClear());

  it('lists the prescription and offers to start a scheduled session', () => {
    sessionData = { ...base, status: 'scheduled' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Upper Body B')).toBeInTheDocument();
    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText(/4 × 8/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start workout/i })).toBeInTheDocument();
  });

  it('navigates to the tracker when starting', async () => {
    sessionData = { ...base, status: 'scheduled' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /start workout/i }));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9/track');
  });

  it('shows logged results and no start action for a completed session', () => {
    sessionData = {
      ...base,
      status: 'completed',
      logged_sets: [
        {
          id: 1,
          workout_exercise_id: 3,
          set_number: 1,
          actual_weight: 80,
          actual_reps: 8,
          actual_rpe: 8,
          effort_method: 'rpe',
        },
      ],
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/80 × 8/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start workout/i })).not.toBeInTheDocument();
  });

  it('offers to start a future session early', () => {
    sessionData = { ...base, status: 'scheduled', scheduled_date: '2099-01-01' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /start early/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/SessionDetailPage.test.tsx`
Expected: FAIL — cannot resolve `@/pages/SessionDetailPage`

- [ ] **Step 3: Write the page**

Create `frontend/src/pages/SessionDetailPage.tsx`:

```typescript
import { useNavigate, useParams } from 'react-router-dom';
import { useSession } from '@/hooks/useSession';
import { toIsoDate } from '@/hooks/useSchedule';
import { Alert, Button, Card, SessionStatusBadge, Spinner } from '@/components';
import type { LoggedSet } from '@/types/session';

export default function SessionDetailPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const id = sessionId ? Number(sessionId) : null;
  const { data: session, isLoading, error } = useSession(id);

  if (isLoading) return <Spinner />;

  if (error || !session) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-4">
        <Card padding="lg" className="text-center">
          <p className="body-md text-error-600 mb-4">This session could not be loaded.</p>
          <Button onClick={() => navigate('/schedule')}>Back to schedule</Button>
        </Card>
      </div>
    );
  }

  const today = toIsoDate(new Date());
  const isDone = session.status === 'completed';
  const isFuture = session.scheduled_date > today;
  const canStart = !isDone && session.status !== 'skipped';

  const [y, m, d] = session.scheduled_date.split('-').map(Number);
  const dateLabel = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const setsFor = (workoutExerciseId: number): LoggedSet[] =>
    session.logged_sets
      .filter((s) => s.workout_exercise_id === workoutExerciseId)
      .sort((a, b) => a.set_number - b.set_number);

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4 pb-28">
      <div className="max-w-2xl mx-auto">
        <Button variant="secondary" className="mb-4" onClick={() => navigate('/schedule')}>
          ← Schedule
        </Button>

        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <p className="label-sm text-neutral-600 dark:text-neutral-400">
              {dateLabel} • Week {session.week}
            </p>
            <SessionStatusBadge
              status={session.status}
              scheduledDate={session.scheduled_date}
              today={today}
            />
          </div>
          <h1 className="display-md">{session.workout_name}</h1>
          <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {session.program_name} • {session.exercise_count} exercises • {session.duration_min} min
          </p>
        </div>

        {session.reactive_deload && session.deload_reason && (
          <Alert type="info" className="mb-4">
            {session.deload_reason}
          </Alert>
        )}

        <Card padding="md">
          <ol className="divide-y divide-neutral-200 dark:divide-neutral-700">
            {session.slots.map((slot, index) => {
              const logged = setsFor(slot.workout_exercise_id);
              return (
                <li
                  key={slot.workout_exercise_id}
                  className="py-3 flex items-baseline justify-between gap-4"
                >
                  <span className="body-md text-neutral-900 dark:text-neutral-50">
                    {index + 1}. {slot.exercise_name}
                  </span>
                  <span className="body-sm text-neutral-600 dark:text-neutral-400 text-right">
                    {logged.length > 0
                      ? logged
                          .map((s) => `${s.actual_weight ?? '—'} × ${s.actual_reps ?? '—'}`)
                          .join('  ')
                      : `${slot.sets} × ${slot.reps}${slot.load ? ` @ ${slot.load}` : ''}`}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      </div>

      {canStart && (
        <div className="fixed bottom-0 left-0 right-0 px-4 pb-4 bg-gradient-to-t from-neutral-50 dark:from-neutral-900">
          <div className="max-w-2xl mx-auto">
            <Button className="w-full" onClick={() => navigate(`/sessions/${session.session_id}/track`)}>
              {isFuture ? 'Start early' : 'Start workout'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Add the route**

In `frontend/src/App.tsx`, import the page and add:

```typescript
<Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/SessionDetailPage.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
docker-compose exec frontend npm run lint -- --fix && docker-compose exec frontend npm run type-check
git add frontend/src/pages/SessionDetailPage.tsx frontend/src/App.tsx frontend/src/tests/pages/SessionDetailPage.test.tsx
git commit -m "feat(sessions): add the session detail page"
```

---

## Task 15: Extract useSessionProgress

**Files:**
- Create: `frontend/src/hooks/useSessionProgress.ts`
- Test: `frontend/src/tests/hooks/useSessionProgress.test.tsx`

**Interfaces:**
- Consumes: `SlotPreview` from `@/types/program`.
- Produces: `useSessionProgress(slots: SlotPreview[])` returning
  `{ exercises, currentIndex, currentExercise, completedSetsCount, isExerciseComplete, completedExercises, progressPercentage, isLastExercise, recordSet, goToNext }`.
  `recordSet(set: { weight?: number; reps?: number; effort?: number; effort_method?: EffortMethod })` appends to the current exercise and returns `true` when that append completed it.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/hooks/useSessionProgress.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import type { SlotPreview } from '@/types/program';

const slot = (id: number, name: string, sets: number): SlotPreview => ({
  workout_exercise_id: id,
  exercise_id: id,
  exercise_name: name,
  sets,
  reps: 8,
  load: 80,
  rest_seconds: 120,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
});

describe('useSessionProgress', () => {
  it('starts on the first exercise with nothing logged', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 2), slot(2, 'Row', 2)]));

    expect(result.current.currentExercise?.exercise_name).toBe('Bench');
    expect(result.current.completedSetsCount).toBe(0);
    expect(result.current.progressPercentage).toBe(0);
  });

  it('reports completion once the target set count is reached', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 2)]));

    act(() => {
      result.current.recordSet({ weight: 80, reps: 8 });
    });
    expect(result.current.isExerciseComplete).toBe(false);

    act(() => {
      result.current.recordSet({ weight: 80, reps: 8 });
    });
    expect(result.current.isExerciseComplete).toBe(true);
    expect(result.current.progressPercentage).toBe(100);
  });

  it('advances to the next exercise', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 1), slot(2, 'Row', 1)]));

    act(() => {
      result.current.goToNext();
    });

    expect(result.current.currentExercise?.exercise_name).toBe('Row');
    expect(result.current.isLastExercise).toBe(true);
  });

  it('does not advance past the last exercise', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 1)]));

    act(() => {
      result.current.goToNext();
    });

    expect(result.current.currentIndex).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/hooks/useSessionProgress.test.tsx`
Expected: FAIL — cannot resolve `@/hooks/useSessionProgress`

- [ ] **Step 3: Write the hook**

Create `frontend/src/hooks/useSessionProgress.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react';
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';

export interface LoggedSetEntry {
  setNumber: number;
  weight?: number;
  reps?: number;
  effort?: number;
  effort_method?: EffortMethod;
  timestamp: Date;
}

export interface ExerciseProgress extends SlotPreview {
  completedSets: LoggedSetEntry[];
}

export function useSessionProgress(slots: SlotPreview[]) {
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    setExercises(slots.map((slot) => ({ ...slot, completedSets: [] })));
    setCurrentIndex(0);
  }, [slots]);

  const currentExercise = exercises[currentIndex] ?? null;
  const completedSetsCount = currentExercise?.completedSets.length ?? 0;
  const isExerciseComplete = currentExercise ? completedSetsCount >= currentExercise.sets : false;
  const completedExercises = exercises.filter((ex) => ex.completedSets.length >= ex.sets).length;
  const progressPercentage = exercises.length
    ? (completedExercises / exercises.length) * 100
    : 0;
  const isLastExercise = currentIndex === exercises.length - 1;

  const recordSet = useCallback(
    (set: Omit<LoggedSetEntry, 'setNumber' | 'timestamp'>): boolean => {
      let didComplete = false;
      setExercises((prev) => {
        const next = prev.map((ex, i) =>
          i === currentIndex
            ? {
                ...ex,
                completedSets: [
                  ...ex.completedSets,
                  { ...set, setNumber: ex.completedSets.length + 1, timestamp: new Date() },
                ],
              }
            : ex,
        );
        didComplete = next[currentIndex].completedSets.length >= next[currentIndex].sets;
        return next;
      });
      return didComplete;
    },
    [currentIndex],
  );

  const goToNext = useCallback(() => {
    setCurrentIndex((i) => (i < exercises.length - 1 ? i + 1 : i));
  }, [exercises.length]);

  return {
    exercises,
    currentIndex,
    currentExercise,
    completedSetsCount,
    isExerciseComplete,
    completedExercises,
    progressPercentage,
    isLastExercise,
    recordSet,
    goToNext,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- src/tests/hooks/useSessionProgress.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
docker-compose exec frontend npm run type-check
git add frontend/src/hooks/useSessionProgress.ts frontend/src/tests/hooks/useSessionProgress.test.tsx
git commit -m "refactor(tracking): extract session progress into a hook"
```

---

## Task 16: Retarget WorkoutTrackingPage to sessions

**Files:**
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx`
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/hooks/useWorkoutDetails.ts`
- Delete: `frontend/src/tests/hooks/useWorkoutDetails.test.tsx`
- Test: `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx`

**Interfaces:**
- Consumes: `useSession` (Task 11), `useSessionProgress` (Task 15), `logSessionSet` / `postSessionReadiness` / `completeSession` (Task 10).
- Produces: the `/sessions/:sessionId/track` route.

- [ ] **Step 1: Rewrite the page test**

Replace `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx` with:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';

const navigateMock = vi.fn();
const completeSessionMock = vi.fn();
const logSessionSetMock = vi.fn();

vi.mock('@/api/sessions', () => ({
  logSessionSet: (...args: unknown[]) => logSessionSetMock(...args),
  postSessionReadiness: vi.fn().mockResolvedValue(undefined),
  completeSession: (...args: unknown[]) => completeSessionMock(...args),
}));

const slot = {
  workout_exercise_id: 3,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 1,
  reps: 8,
  load: 80,
  rest_seconds: 120,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
};

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({
    data: {
      session_id: 9,
      scheduled_date: '2026-07-27',
      week: 3,
      status: 'scheduled',
      workout_id: 4,
      workout_name: 'Upper Body B',
      exercise_count: 1,
      duration_min: 45,
      program_id: 1,
      program_name: 'My Program',
      slots: [slot],
      logged_sets: [],
      completed_at: null,
      reactive_deload: false,
      deload_reason: null,
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({ userProfile: { effort_method: 'rpe' } }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ sessionId: '9' }) };
});

describe('WorkoutTrackingPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    completeSessionMock.mockClear().mockResolvedValue({});
    logSessionSetMock.mockClear().mockResolvedValue(undefined);
  });

  it('logs the current exercise from the session slots', () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText(/Exercise 1 of 1/)).toBeInTheDocument();
  });

  it('returns to the dashboard root, not /dashboard, after completing', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });
});
```

The "Complete Workout" button only renders once the last exercise is complete. If the second test cannot reach it, log the single set through the `SetLogger` first — read `frontend/src/components/SetLogger.tsx` for its field labels and submit button, and drive it the way `SetLogger.test.tsx` does.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/WorkoutTrackingPage.test.tsx`
Expected: FAIL — the page still reads `workoutId` and `useWorkoutDetails`.

- [ ] **Step 3: Retarget the page**

In `frontend/src/pages/WorkoutTrackingPage.tsx`:

1. Replace the `useWorkoutDetails` import with `import { useSession } from '@/hooks/useSession';`, and the `logSetLog` / `postWorkoutReadiness` imports with `import { logSessionSet, postSessionReadiness, completeSession } from '@/api/sessions';`.
2. Add `import { useSessionProgress } from '@/hooks/useSessionProgress';`.
3. Replace the params block:

```typescript
  const { sessionId } = useParams<{ sessionId?: string }>();
  const sessionIdNum = sessionId ? Number(sessionId) : null;
  const { data: session, isLoading, error } = useSession(sessionIdNum);
```

Drop `useSearchParams` and the `programId` derivation entirely.

4. Delete the local `LoggedSet` and `ExerciseProgress` interfaces, the `exercises` / `currentExerciseIndex` state, and the `useEffect` that seeds them. Replace with:

```typescript
  const {
    currentExercise,
    currentIndex,
    exercises,
    completedSetsCount,
    isExerciseComplete,
    completedExercises,
    progressPercentage,
    isLastExercise,
    recordSet,
    goToNext,
  } = useSessionProgress(session?.slots ?? []);
```

5. Replace `handleLogSet` with:

```typescript
  const handleLogSet = async (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => {
    if (!sessionIdNum || !currentExercise) return;

    try {
      await logSessionSet(sessionIdNum, {
        workout_exercise_id: currentExercise.workout_exercise_id,
        set_number: completedSetsCount + 1,
        actual_weight: data.weight,
        actual_reps: data.reps,
        actual_rpe: data.effort,
        effort_method: effortMethod,
      });

      const didComplete = recordSet({
        weight: data.weight,
        reps: data.reps,
        effort: data.effort,
        effort_method: data.effort_method,
      });

      if (!didComplete) {
        const remaining = currentExercise.sets - (completedSetsCount + 1);
        setToast({ message: `Set logged! ${remaining} more to go! 💪`, icon: '✓' });
        return;
      }

      setToast({ message: `Great! ${currentExercise.exercise_name} complete! 💪`, icon: '🎉' });

      if (!isLastExercise) {
        const nextName = exercises[currentIndex + 1].exercise_name;
        setTimeout(() => {
          goToNext();
          setToast({ message: `Next up: ${nextName}`, icon: '▶️' });
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to log set:', err);
      setToast({ message: 'Failed to log set. Please try again.', icon: '⚠️' });
    }
  };
```

6. Replace `handleSubmitReadiness` with:

```typescript
  const handleSubmitReadiness = async (readiness: number) => {
    if (!sessionIdNum) return;
    const phase = readinessOpen === 'pre' ? 'pre' : 'post';

    try {
      await postSessionReadiness(sessionIdNum, readiness, phase);
      setToast({ message: `Readiness recorded: ${readiness}/5`, icon: '✓' });

      if (phase === 'post') {
        await completeSession(sessionIdNum);
        navigate('/');
      }
    } catch (err) {
      console.error('Failed to record readiness:', err);
      setToast({ message: 'Failed to record readiness. Please try again.', icon: '⚠️' });
    } finally {
      setReadinessOpen(null);
    }
  };
```

The `navigate('/')` is the fix for the dead `/dashboard` target.

7. In the JSX, replace `workoutDetails` with `session`, `currentExerciseIndex` with `currentIndex`, and `totalExercises` with `exercises.length`. Guard the whole render on `if (!session || !currentExercise) return <Spinner />;`. In the bottom bar, swap the button condition:

```typescript
          {isExerciseComplete && isLastExercise ? (
            <Button className="w-full" onClick={handleCompleteWorkout}>
              Complete Workout
            </Button>
          ) : isExerciseComplete ? (
            <Button className="w-full" onClick={goToNext}>
              Next Exercise
            </Button>
          ) : (
```

- [ ] **Step 4: Update the route and delete the dead hook**

In `frontend/src/App.tsx`, replace the `/workouts/:workoutId` route with:

```typescript
<Route path="/sessions/:sessionId/track" element={<WorkoutTrackingPage />} />
```

Then:

```bash
rm frontend/src/hooks/useWorkoutDetails.ts frontend/src/tests/hooks/useWorkoutDetails.test.tsx
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose exec frontend npm run test`
Expected: PASS. Any suite still importing `useWorkoutDetails` must be updated, not re-added.

- [ ] **Step 6: Commit**

```bash
docker-compose exec frontend npm run lint -- --fix && docker-compose exec frontend npm run type-check
git add -A frontend/src
git commit -m "feat(tracking): drive workout tracking from sessions"
```

---

## Task 17: Rewire the dashboard card

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx:11-91`
- Modify: `frontend/src/components/WorkoutCard.tsx`
- Modify: `frontend/src/api/logging.ts`, `frontend/src/api/workouts.ts`
- Test: `frontend/src/tests/pages/DashboardPage.test.tsx`, `frontend/src/tests/components/WorkoutCard.test.tsx`

**Interfaces:**
- Consumes: `useTodaySession` (Task 11).
- Produces: `WorkoutCardProps` becomes `{ entry: ScheduleEntry; programName: string; onSelect: () => void }`.

- [ ] **Step 1: Rewrite the dashboard test**

Replace `frontend/src/tests/pages/DashboardPage.test.tsx` with:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '@/pages/DashboardPage';

const navigateMock = vi.fn();
let todaySession: unknown = null;
let programData: unknown = null;

vi.mock('@/hooks/useSchedule', () => ({
  useTodaySession: () => ({ session: todaySession, isLoading: false }),
}));

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      user: { id: 1, email: 'a@b.com', first_name: 'Jorge', last_name: 'C' },
      userProfile: { workout_duration_min: 45 },
    }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const entry = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 3,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 5,
  duration_min: 45,
};

describe('DashboardPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    todaySession = null;
    programData = { program_id: 1, name: 'My Program', status: 'active', duration_weeks: 8 };
  });

  it("shows today's session when one is scheduled", () => {
    todaySession = entry;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Upper Body B')).toBeInTheDocument();
  });

  it('opens the session detail in one click', async () => {
    todaySession = entry;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /Upper Body B/i }));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
  });

  it('falls back to a schedule link when nothing is scheduled today', async () => {
    todaySession = null;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/nothing scheduled today/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /view schedule/i }));
    expect(navigateMock).toHaveBeenCalledWith('/schedule');
  });

  it('prompts to create a program when there is none', () => {
    programData = null;
    todaySession = null;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /create program/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- src/tests/pages/DashboardPage.test.tsx`
Expected: FAIL — the page still calls `getTodayWorkout` off the program preview.

- [ ] **Step 3: Update WorkoutCard**

Change `frontend/src/components/WorkoutCard.tsx` to take a `ScheduleEntry`:

```typescript
import type { ScheduleEntry } from '@/types/session';
import { Card } from '@/components';

export interface WorkoutCardProps {
  entry: ScheduleEntry;
  programName: string;
  onSelect: () => void;
}

export function WorkoutCard({ entry, programName, onSelect }: WorkoutCardProps) {
  const exerciseLabel = `${entry.exercise_count} ${entry.exercise_count === 1 ? 'exercise' : 'exercises'}`;
  const meta = `${programName} • Week ${entry.week} • ${exerciseLabel} • ${entry.duration_min} min`;

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={`Start ${entry.workout_name}, ${programName} week ${entry.week}, ${exerciseLabel}, ${entry.duration_min} minutes`}
      className="block w-full text-left rounded-lg transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <Card padding="md" className="border-l-4 border-primary-600">
        <span className="flex items-center justify-between gap-4">
          <span className="block min-w-0">
            <span className="label-sm text-primary-700 dark:text-primary-400 tracking-wide block">
              Today
            </span>
            <span className="heading-lg text-neutral-900 dark:text-neutral-50 block truncate">
              {entry.workout_name}
            </span>
            <span className="body-sm text-neutral-600 dark:text-neutral-400 mt-1 block">
              {meta}
            </span>
          </span>
          <span
            aria-hidden="true"
            className="shrink-0 body-sm font-medium text-primary-700 dark:text-primary-400"
          >
            View →
          </span>
        </span>
      </Card>
    </button>
  );
}
```

Update `frontend/src/tests/components/WorkoutCard.test.tsx` to build a `ScheduleEntry` and pass `entry` / `onSelect`, preserving its existing assertions about the heading and meta line.

- [ ] **Step 4: Update the dashboard**

In `frontend/src/pages/DashboardPage.tsx`, replace the `useActiveProgram`-derived `getTodayWorkout` block (lines 11-35) with:

```typescript
  const { data: program, isLoading: programLoading } = useActiveProgram();
  const { session: todaySession, isLoading } = useTodaySession();
```

Add `import { useTodaySession } from '@/hooks/useSchedule';`, and replace the "Today's Workout Section" block (lines 52-91) with:

```tsx
        {!program ? (
          <Card padding="lg" className="mb-8 border-l-4 border-secondary-600">
            <h2 className="heading-lg mb-2">Get Started</h2>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create your first workout program to get started.
            </p>
            <Button variant="primary" onClick={() => navigate('/programs/new')}>
              Create Program
            </Button>
          </Card>
        ) : isLoading ? (
          <Card padding="lg" className="mb-8 flex items-center justify-center gap-3">
            <Spinner size="sm" />
            <p className="body-md text-neutral-600 dark:text-neutral-400">Loading workout...</p>
          </Card>
        ) : todaySession ? (
          <div className="mb-8">
            <h2 className="sr-only">Today&apos;s workout</h2>
            <WorkoutCard
              entry={todaySession}
              programName={program.name}
              onSelect={() => navigate(`/sessions/${todaySession.session_id}`)}
            />
          </div>
        ) : (
          <Card padding="lg" className="mb-8 border-l-4 border-neutral-300 dark:border-neutral-600">
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Nothing scheduled today.
            </p>
            <Button variant="secondary" onClick={() => navigate('/schedule')}>
              View schedule →
            </Button>
          </Card>
        )}
```

Delete the now-unused `getTodayWorkout`, `displayWeekNumber`, and `activeProgramId`, and change the "This Week" section's guard from `activeProgramId && program` to `program`.

- [ ] **Step 5: Point the legacy API modules at sessions**

`frontend/src/api/logging.ts` and `frontend/src/api/workouts.ts` are now unused by the tracking page. Delete `logSetLog` and `postWorkoutReadiness` if nothing else imports them:

```bash
docker-compose exec frontend grep -rn "logSetLog\|postWorkoutReadiness" src/
```

Delete each function with no remaining callers, and delete the file if it ends up empty. Leave anything still referenced alone.

- [ ] **Step 6: Run the full frontend suite**

Run: `docker-compose exec frontend npm run test`
Expected: PASS across all suites.

- [ ] **Step 7: Commit**

```bash
docker-compose exec frontend npm run lint -- --fix && docker-compose exec frontend npm run type-check
git add -A frontend/src
git commit -m "feat(dashboard): drive the workout card from today's session"
```

---

## Task 18: Full-stack verification

**Files:** none — verification only.

- [ ] **Step 1: Run the whole backend suite**

Run: `docker-compose exec backend pytest`
Expected: PASS, no skips beyond those already present on `main`.

- [ ] **Step 2: Run backend quality gates**

```bash
docker-compose exec backend ruff check .
docker-compose exec backend black --check .
docker-compose exec backend mypy app/
```
Expected: all clean.

- [ ] **Step 3: Run the whole frontend suite and gates**

```bash
docker-compose exec frontend npm run test
docker-compose exec frontend npm run lint
docker-compose exec frontend npm run type-check
```
Expected: all clean.

- [ ] **Step 4: Verify the migration from empty**

```bash
docker-compose down -v && docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m app.db.seed.seed_exercises
```
Expected: migration applies cleanly to a fresh database; `alembic heads` reports one head.

- [ ] **Step 5: Walk the flow by hand**

Create a program, accept it, then confirm: `/schedule` lists the current week with correct dates; prev/next moves weeks and the URL `?week=` follows; tapping a session opens `/sessions/:id` with the right prescription for that week; Start opens the tracker; logging a set then reloading `/sessions/:id` shows it as in progress with the set recorded; completing returns to `/` and the session reads done; a past unstarted session reads missed.

- [ ] **Step 6: Report**

State plainly which of the above passed and which did not. Do not mark the plan complete with any step failing.

---

## Notes for the implementer

- **`workout_id` is a template id, not a session id.** If you find yourself keying anything user-facing off `workout_id` alone, stop — that is the bug this whole plan exists to remove.
- **`_load` in `programs.py` is the reference** for turning a program into a `(program, definition)` pair. Reuse it; do not reimplement template resolution.
- **The `useSchedule` mock in the page tests uses `importActual`** so that `weekRange` and `toIsoDate` stay real while `useSchedule` is stubbed. Keep that shape — stubbing the whole module breaks the week arithmetic under test.
- **Pre-existing wart, leave alone:** `backend/app/api/v1/endpoints/logging.py` exposes two routers (`router` and `users_workout_router`) with overlapping responsibilities. Not in scope.
