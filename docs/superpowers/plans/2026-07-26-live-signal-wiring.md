# Live Signal Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `_preview_out` load and pass real `set_logs_by_exercise`/`readiness_logs` into `derive_week` for a program's current active week only, so the already-built adjustment/deload-reason banner reflects real user data instead of always showing nominal previews.

**Architecture:** Add a real, user-chosen `start_date` to program creation (schema + drafting + wizard form), backfill it for pre-existing rows via migration, add a program-scoped readiness-log query, then gate `_preview_out`'s existing `derive_week` call so only the week matching `(today - start_date).days // 7 + 1` (when the program is `ACTIVE`) receives live `set_logs_by_exercise`/`readiness_logs`; every other week/status keeps today's nominal behavior.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), React + TypeScript + Vitest/Testing Library (frontend), pytest-asyncio + SQLite in-memory (backend tests).

**Spec:** `docs/superpowers/specs/2026-07-26-live-signal-wiring-design.md`

## Global Constraints

- TDD: write the failing test before the implementation, for every step below (project convention, CLAUDE.md).
- All I/O (DB) stays `async`/`await`.
- Backend: strict type hints; keep `mypy` clean.
- Frontend: TypeScript `strict: true` — test files are type-checked too (`tsconfig.json` includes `src`), so mocks/fixtures that satisfy a typed interface must be updated whenever that interface gains a required field.
- Live signals (autoregulation factor, reactive deload) apply to **exactly one week** of **one program** per preview request: that program's current week, and only while `program.status == ACTIVE`. Every other week/status renders nominally (`autoreg_factor == 1.0`, no reactive deload) — this is the behavior every test in Task 4 verifies.
- No changes to `derive_week`, `compute_adjustment`, or `compute_deload_trigger` (`backend/app/services/program/preview.py`, `backend/app/services/progression/autoregulation.py`, `backend/app/services/progression/deload.py`) — all three already have the right shape; this plan only supplies real arguments to `derive_week`.
- `build_draft`'s new `start_date` parameter must default to `None` (not be strictly required) — it is required at the HTTP layer (`DraftRequest.start_date: date`), but ~58 existing service-level tests across `test_drafting.py`, `test_preview.py`, `test_versioning.py`, `test_adaptation.py`, `test_programs_progression_style.py`, and `tests/harness/runner.py` call `build_draft` directly and have nothing to do with this feature; none of them assert anything about `start_date`, so a default keeps them green without a 58-call-site mechanical edit. Every real caller (the `/programs/draft` endpoint) always passes a real value because the schema field is required.

---

## Task 1: Persist `start_date` at draft time

**Files:**
- Modify: `backend/app/schemas/program_api.py:71` (`DraftRequest`)
- Modify: `backend/app/services/program/drafting.py:68` (`build_draft` signature), `:102` (`WorkoutProgram(...)` construction)
- Modify: `backend/app/api/v1/endpoints/programs.py:210` (`draft()`'s `build_draft(...)` call)
- Modify: `backend/tests/test_programs_flow.py` (5 existing `body` dicts that feed a draft call, + 2 new tests)
- Modify: `backend/tests/test_telemetry_endpoints.py:17` (`_match_body` helper)

**Interfaces:**
- Consumes: existing `DraftRequest(MatchRequest)` schema, existing `build_draft(...)` signature, existing `WorkoutProgram` model (`start_date: date | None` column already exists — see `backend/app/models/program.py:65`).
- Produces: `DraftRequest.start_date: date` (required on the wire); `build_draft(..., start_date: date | None = None, ...)`; every `WorkoutProgram` created via the real `/programs/draft` endpoint now has a real `start_date`. Task 4 depends on this to compute "current week".

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_programs_flow.py` (near the other draft-related tests, e.g. after `test_draft_malformed_required_inputs_returns_422`):

```python
@pytest.mark.asyncio
async def test_draft_requires_start_date(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment
):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
        "start_date": "2026-08-03",
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()["matches"][0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    del draft_body["start_date"]
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_draft_persists_submitted_start_date(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
        "start_date": "2026-08-03",
    }
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    template_id = r.json()["matches"][0]["template_id"]

    draft_body = {**body, "template_id": template_id, "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201
    pid = r.json()["program_id"]

    row = await db_session.execute(text("SELECT start_date FROM workout_programs WHERE id = :pid"), {"pid": pid})
    assert row.scalar_one() == "2026-08-03"
```

Both tests use the file's existing `text` import (already imported at the top of `test_programs_flow.py`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec backend pytest tests/test_programs_flow.py -k "start_date" -v`
Expected: `test_draft_requires_start_date` FAILS (endpoint currently accepts the request and returns 201, not 422 — `start_date` isn't a field yet). `test_draft_persists_submitted_start_date` FAILS (`start_date` column stays `NULL`, not `'2026-08-03'`).

- [ ] **Step 3: Add `start_date` to `DraftRequest`**

In `backend/app/schemas/program_api.py`, add the import and field:

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
```

```python
class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}
    effort_method: EffortMethod | None = None
    start_date: date
```

- [ ] **Step 4: Thread `start_date` through `build_draft`**

In `backend/app/services/program/drafting.py`, add the import:

```python
from datetime import date
from typing import Any
```

Add the new keyword-only parameter (after `duration_weeks`, before `weight_unit`) and pass it into the `WorkoutProgram(...)` construction:

```python
def build_draft(
    template: ProgramTemplate,
    definition: TemplateDefinition,
    ctx: SelectionContext,
    exercises: list[Exercise],
    *,
    user_id: int,
    environment_id: int,
    days_per_week: int,
    duration_weeks: int,
    start_date: date | None = None,
    weight_unit: str,
    required_inputs: dict[str, float],
    progression_style: str = "consistent",
    effort_method: str | None = None,
    variety_preference: str = "low",
    engine_config_version: str = "unversioned",
    model_version: str | None = None,
    ranking_weights_version: str | None = None,
    config: EngineConfig | None = None,
    telemetry_sink: list[dict[str, Any]] | None = None,
    advisory_sink: list[Advisory] | None = None,
    regression_graphs: RegressionGraphsConfig | None = None,
) -> WorkoutProgram:
```

```python
    program = WorkoutProgram(
        user_id=user_id,
        template_id=template.id,
        environment_id=environment_id,
        name=template.name,
        focus=(template.goals[0] if template.goals else None),
        status=ProgramStatus.DRAFT,
        duration_weeks=duration_weeks,
        days_per_week=days_per_week,
        start_date=start_date,
        weight_unit=weight_unit,
        model_version=resolved_model_version,
        ranking_weights_version=resolved_ranking_weights_version,
        constraints={
```

(`start_date` defaults to `None` — see Global Constraints for why this is a default here even though it's required at the schema layer.)

- [ ] **Step 5: Pass `data.start_date` from the endpoint**

In `backend/app/api/v1/endpoints/programs.py`, in `draft()`:

```python
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=user.id,
        environment_id=environment.id,
        days_per_week=data.days_per_week,
        duration_weeks=data.duration_weeks,
        start_date=data.start_date,
        weight_unit=data.weight_unit,
        required_inputs=data.required_inputs,
        progression_style=data.progression_style.value,
        effort_method=data.effort_method.value if data.effort_method else None,
        variety_preference=data.variety_preference.value,
        engine_config_version=engine_config.config_version,
        telemetry_sink=telemetry_sink,
        advisory_sink=advisory_sink,
    )
```

- [ ] **Step 6: Fix existing tests broken by the now-required field**

`DraftRequest.start_date` is required, so every existing test that POSTs to `/api/v1/programs/draft` needs a `start_date` in its request body. Add `"start_date": "2026-01-05"` to these 5 `body` dicts in `backend/tests/test_programs_flow.py` (the value is arbitrary — none of these tests exercise the live-signal feature):

In `test_full_flow`:
```python
    body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
        "start_date": "2026-01-05",
    }
```

Apply the identical `"start_date": "2026-01-05",` addition to the `body` dicts in:
- `test_exclude_persists_to_db_not_just_in_memory_response`
- `test_draft_stores_engine_config_version_in_constraints`
- `test_draft_malformed_required_inputs_returns_422`
- `_drafted_program_id` (the shared helper used by the check-in tests)

In `backend/tests/test_telemetry_endpoints.py`, fix it once at the source — the shared `_match_body` helper:

```python
def _match_body(environment_id: int) -> dict:
    return {
        "environment_id": environment_id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 8,
        "start_date": "2026-01-05",
    }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker-compose exec backend pytest tests/test_programs_flow.py tests/test_telemetry_endpoints.py -v`
Expected: all PASS, including the two new tests from Step 1.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/program_api.py backend/app/services/program/drafting.py backend/app/api/v1/endpoints/programs.py backend/tests/test_programs_flow.py backend/tests/test_telemetry_endpoints.py
git commit -m "feat(backend): persist a real start_date at program-draft time"
```

---

## Task 2: Backfill `start_date` for existing programs

**Files:**
- Create: `backend/alembic/versions/9f1a2b3c4d5e_backfill_start_date_on_workout_programs.py`
- Create: `backend/tests/test_start_date_backfill.py`

**Interfaces:**
- Consumes: `workout_programs.created_at` (always non-null), `workout_programs.start_date` (nullable, existing column).
- Produces: no code interface — this is a one-time data migration. Task 4's "current week" math depends on pre-existing `ACTIVE` programs having a non-null `start_date` after this runs.

This task doesn't follow the usual red/green TDD ordering: the migration is a single `UPDATE` statement with no function signature to fail against. Instead, the test below locks in the exact SQL string's behavior first; the migration file then reuses that identical string, so the test doubles as regression coverage for the migration.

- [ ] **Step 1: Write the test**

Create `backend/tests/test_start_date_backfill.py`:

```python
from datetime import date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramStatus, User, WorkoutProgram

_BACKFILL_SQL = "UPDATE workout_programs SET start_date = date(created_at) WHERE start_date IS NULL"


async def _make_program(
    db_session: AsyncSession, user: User, *, start_date: date | None, created_at: datetime
) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=user.id,
        template_id=1,
        environment_id=1,
        name="Backfill Test",
        status=ProgramStatus.DRAFT,
        duration_weeks=8,
        days_per_week=3,
        start_date=start_date,
        weight_unit="kg",
        constraints={},
        created_at=created_at,
    )
    db_session.add(program)
    await db_session.commit()
    await db_session.refresh(program)
    return program


@pytest.mark.asyncio
async def test_backfill_sets_start_date_from_created_at_only_when_null(
    db_session: AsyncSession, test_user: User
):
    needs_backfill = await _make_program(
        db_session, test_user, start_date=None, created_at=datetime(2026, 3, 15, 10, 30)
    )
    already_set = await _make_program(
        db_session, test_user, start_date=date(2026, 6, 1), created_at=datetime(2026, 1, 1)
    )

    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()

    await db_session.refresh(needs_backfill)
    await db_session.refresh(already_set)
    assert needs_backfill.start_date == date(2026, 3, 15)
    assert already_set.start_date == date(2026, 6, 1)


@pytest.mark.asyncio
async def test_backfill_is_idempotent(db_session: AsyncSession, test_user: User):
    program = await _make_program(
        db_session, test_user, start_date=None, created_at=datetime(2026, 3, 15, 10, 30)
    )

    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()
    await db_session.execute(text(_BACKFILL_SQL))
    await db_session.commit()

    await db_session.refresh(program)
    assert program.start_date == date(2026, 3, 15)
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_start_date_backfill.py -v`
Expected: both tests PASS — this proves the `_BACKFILL_SQL` string is correct (NULL-only, idempotent) before it's baked into a migration file.

- [ ] **Step 3: Create the migration**

Create `backend/alembic/versions/9f1a2b3c4d5e_backfill_start_date_on_workout_programs.py`:

```python
"""backfill start_date on workout_programs

Revision ID: 9f1a2b3c4d5e
Revises: 6b1a2c3d4e5f
Create Date: 2026-07-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f1a2b3c4d5e"
down_revision: Union[str, None] = "6b1a2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows (any status) predate WorkoutProgram.start_date ever being
    # written - approximate it from created_at so "current week" math
    # (app/api/v1/endpoints/programs.py::_preview_out) has something to work
    # with for programs accepted before this migration shipped.
    op.execute("UPDATE workout_programs SET start_date = date(created_at) WHERE start_date IS NULL")


def downgrade() -> None:
    # Backfilled values are approximations derived from created_at, not real
    # user input - there's nothing meaningful to restore on downgrade.
    pass
```

- [ ] **Step 4: Apply the migration to the local dev database**

Run: `docker-compose exec backend alembic upgrade head`
Expected: migration `9f1a2b3c4d5e` applies cleanly with no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/9f1a2b3c4d5e_backfill_start_date_on_workout_programs.py backend/tests/test_start_date_backfill.py
git commit -m "feat(backend): backfill start_date for programs created before it existed"
```

---

## Task 3: Program-scoped readiness-log query

**Files:**
- Modify: `backend/app/crud/logging.py` (new function, after `get_set_logs`)
- Modify: `backend/tests/test_logging.py` (new tests + imports)

**Interfaces:**
- Consumes: existing `UserWorkoutLog` model (`backend/app/models/logging.py`), existing `test_program_with_workout` fixture (`backend/tests/test_logging.py`).
- Produces: `async def get_workout_logs_for_workouts(db: AsyncSession, workout_ids: list[int], user_id: int, since: date) -> list[UserWorkoutLog]`. Task 4 imports and calls this directly.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_logging.py`, update the imports at the top:

```python
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password
from app.crud import logging as crud_logging
from app.models import ProgramStatus, User, UserWorkoutLog, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.logging import UserWorkoutLogCreate, WorkoutSetLogCreate
from app.services.auth import create_tokens
```

Append these two tests at the end of the file:

```python
@pytest.mark.asyncio
async def test_get_workout_logs_for_workouts_scopes_to_given_workout_ids(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple
):
    """Readiness logs must be scoped to one program's workouts, not the user's
    full cross-program history - otherwise a signal from an unrelated program
    would leak into this one's reactive-deload trigger."""
    _, workout, _ = test_program_with_workout

    other_program = WorkoutProgram(
        user_id=test_user.id,
        template_id=1,
        environment_id=1,
        name="Other Program",
        status=ProgramStatus.ACTIVE,
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    db_session.add(other_program)
    await db_session.flush()
    other_workout = Workout(program_id=other_program.id, key="other", name="Other Day", order=1)
    db_session.add(other_workout)
    await db_session.flush()

    in_scope = UserWorkoutLog(
        user_id=test_user.id, workout_id=workout.id, session_date=datetime.utcnow() - timedelta(days=2), readiness=1
    )
    out_of_scope = UserWorkoutLog(
        user_id=test_user.id,
        workout_id=other_workout.id,
        session_date=datetime.utcnow() - timedelta(days=1),
        readiness=1,
    )
    db_session.add_all([in_scope, out_of_scope])
    await db_session.commit()

    since = date.today() - timedelta(days=14)
    logs = await crud_logging.get_workout_logs_for_workouts(db_session, [workout.id], test_user.id, since)

    log_ids = {log.id for log in logs}
    assert in_scope.id in log_ids
    assert out_of_scope.id not in log_ids


@pytest.mark.asyncio
async def test_get_workout_logs_for_workouts_respects_since(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple
):
    _, workout, _ = test_program_with_workout

    recent = UserWorkoutLog(
        user_id=test_user.id, workout_id=workout.id, session_date=datetime.utcnow() - timedelta(days=2), readiness=1
    )
    old = UserWorkoutLog(
        user_id=test_user.id, workout_id=workout.id, session_date=datetime.utcnow() - timedelta(days=30), readiness=1
    )
    db_session.add_all([recent, old])
    await db_session.commit()

    since = date.today() - timedelta(days=14)
    logs = await crud_logging.get_workout_logs_for_workouts(db_session, [workout.id], test_user.id, since)

    log_ids = {log.id for log in logs}
    assert recent.id in log_ids
    assert old.id not in log_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec backend pytest tests/test_logging.py -k "get_workout_logs_for_workouts" -v`
Expected: FAIL with `AttributeError: module 'app.crud.logging' has no attribute 'get_workout_logs_for_workouts'`.

- [ ] **Step 3: Implement the crud function**

In `backend/app/crud/logging.py`, update the top import and add the function after `get_set_logs`:

```python
from datetime import date
from typing import Optional
```

```python
async def get_workout_logs_for_workouts(
    db: AsyncSession, workout_ids: list[int], user_id: int, since: date
) -> list[UserWorkoutLog]:
    """Readiness logs for a specific program's workouts, for the reactive-deload window."""
    stmt = select(UserWorkoutLog).where(
        and_(
            UserWorkoutLog.workout_id.in_(workout_ids),
            UserWorkoutLog.user_id == user_id,
            UserWorkoutLog.session_date >= since,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker-compose exec backend pytest tests/test_logging.py -v`
Expected: all PASS (including the two new tests and every pre-existing test in the file).

- [ ] **Step 5: Commit**

```bash
git add backend/app/crud/logging.py backend/tests/test_logging.py
git commit -m "feat(backend): add program-scoped readiness-log query"
```

---

## Task 4: Wire live signals into `_preview_out`

**Files:**
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Create: `backend/tests/test_programs_live_signals.py`

**Interfaces:**
- Consumes: `get_set_logs(db, workout_id, user_id)` (`app/crud/logging.py:70`, unchanged), `get_workout_logs_for_workouts(db, workout_ids, user_id, since)` (Task 3), `derive_week(program, definition, week, exercises, set_logs_by_exercise=None, readiness_logs=None, ...)` (unchanged, `app/services/program/preview.py:93`), `DELOAD_LOOKBACK_DAYS` (`app/core/constants.py:176`).
- Produces: `_preview_out(db, program, definition, user, advisories=None)` — every call site in this file is updated to pass `user`. No other module calls `_preview_out` (it is module-private).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_programs_live_signals.py`:

```python
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.programs import _preview_out
from app.crud.program import get_program
from app.models import (
    ProgramStatus,
    ProgramTemplate,
    User,
    UserWorkoutLog,
    Workout,
    WorkoutExercise,
    WorkoutProgram,
    WorkoutSetLog,
)
from app.schemas.template import TemplateDefinition


async def _build_program(
    db_session: AsyncSession,
    test_user: User,
    template: ProgramTemplate,
    *,
    status: ProgramStatus,
    start_date: date | None,
    duration_weeks: int = 8,
) -> tuple[WorkoutProgram, Workout, WorkoutExercise]:
    program = WorkoutProgram(
        user_id=test_user.id,
        template_id=template.id,
        environment_id=1,
        name="Live Signal Test",
        status=status,
        duration_weeks=duration_weeks,
        days_per_week=3,
        start_date=start_date,
        weight_unit="kg",
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="day_a", name="Day A", order=1)
    db_session.add(workout)
    await db_session.flush()

    exercise = WorkoutExercise(
        workout_id=workout.id,
        order=1,
        exercise_id=1,
        fills_rule={"priority": "primary"},
        sets=3,
        reps_min=5,
        reps_max=5,
        base_load=100.0,
        rest_seconds=120,
        scheme_key="main",
        target_rpe=8.0,
        is_locked=False,
        is_user_swapped=False,
    )
    db_session.add(exercise)
    await db_session.commit()

    saved = await get_program(db_session, test_user.id, program.id)
    assert saved is not None
    return saved, workout, exercise


async def _add_high_rpe_set_logs(
    db_session: AsyncSession, test_user: User, workout: Workout, exercise: WorkoutExercise
) -> None:
    for days_ago in (2, 5):
        db_session.add(
            WorkoutSetLog(
                user_id=test_user.id,
                workout_id=workout.id,
                workout_exercise_id=exercise.id,
                set_number=1,
                actual_weight=100.0,
                actual_reps=5,
                actual_rpe=9.5,
                effort_method="rpe",
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            )
        )
    await db_session.commit()


async def _add_low_readiness_logs(db_session: AsyncSession, test_user: User, workout: Workout) -> None:
    for days_ago in (2, 5):
        db_session.add(
            UserWorkoutLog(
                user_id=test_user.id,
                workout_id=workout.id,
                session_date=datetime.utcnow() - timedelta(days=days_ago),
                readiness=1,
            )
        )
    await db_session.commit()


@pytest.mark.asyncio
async def test_current_week_gets_live_signals_but_adjacent_weeks_stay_nominal(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=2)  # lands on week 3 of an 8-week program
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    current = result.weeks[3][0]
    assert current.slots[0].adjustment_reason is not None
    assert current.reactive_deload is True
    assert current.deload_reason is not None

    for week in (2, 4):
        day = result.weeks[week][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False
        assert day.deload_reason is None


@pytest.mark.asyncio
async def test_draft_and_archived_programs_never_get_live_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=2)
    for status in (ProgramStatus.DRAFT, ProgramStatus.ARCHIVED):
        program, workout, exercise = await _build_program(
            db_session, test_user, sample_template_orm, status=status, start_date=start_date
        )
        await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
        await _add_low_readiness_logs(db_session, test_user, workout)

        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        result = await _preview_out(db_session, program, definition, test_user)

        day = result.weeks[3][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_future_start_date_yields_no_current_week_and_no_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() + timedelta(days=5)
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=start_date
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    day = result.weeks[1][0]
    assert day.slots[0].adjustment_reason is None
    assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_overrun_start_date_yields_no_current_week_and_no_signals(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    start_date = date.today() - timedelta(weeks=20)
    program, workout, exercise = await _build_program(
        db_session,
        test_user,
        sample_template_orm,
        status=ProgramStatus.ACTIVE,
        start_date=start_date,
        duration_weeks=8,
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    for week in range(1, 9):
        day = result.weeks[week][0]
        assert day.slots[0].adjustment_reason is None
        assert day.reactive_deload is False


@pytest.mark.asyncio
async def test_exact_week_one_boundary_gets_signals_only_on_week_one(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=date.today()
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    assert result.weeks[1][0].slots[0].adjustment_reason is not None
    assert result.weeks[2][0].slots[0].adjustment_reason is None


@pytest.mark.asyncio
async def test_null_start_date_falls_back_to_nominal_without_error(
    db_session: AsyncSession, test_user: User, sample_template_orm: ProgramTemplate
):
    program, workout, exercise = await _build_program(
        db_session, test_user, sample_template_orm, status=ProgramStatus.ACTIVE, start_date=None
    )
    await _add_high_rpe_set_logs(db_session, test_user, workout, exercise)
    await _add_low_readiness_logs(db_session, test_user, workout)

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    result = await _preview_out(db_session, program, definition, test_user)

    day = result.weeks[1][0]
    assert day.slots[0].adjustment_reason is None
    assert day.reactive_deload is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec backend pytest tests/test_programs_live_signals.py -v`
Expected: FAIL with `TypeError: _preview_out() missing 1 required positional argument: 'user'` (or similar) — `_preview_out` doesn't accept a `user` parameter yet.

- [ ] **Step 3: Implement the wiring**

In `backend/app/api/v1/endpoints/programs.py`, add imports:

```python
from datetime import date, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import (
    ProgramNotFoundError,
    ProgramTemplateNotFoundError,
    TrainingEnvironmentNotFoundError,
    WorkoutExerciseNotFoundError,
)
from app.core.constants import DELOAD_LOOKBACK_DAYS
from app.core.database import get_db
from app.crud.checkin import create_check_in, list_check_ins_for_program
from app.crud.exercise import get_exercises_by_ids, list_exercises
from app.crud.injury import list_injury_records
from app.crud.logging import get_set_logs, get_workout_logs_for_workouts
from app.crud.program import get_active_program, get_program, get_template, list_active_templates, save_program
from app.crud.training_environment import get_training_environment
from app.models import (
    CheckIn,
    InjuryRegion,
    ProgramStatus,
    TrainingEnvironment,
    User,
    UserWorkoutLog,
    WorkoutProgram,
    WorkoutSetLog,
)
```

Replace `_preview_out`:

```python
async def _preview_out(
    db: AsyncSession,
    program: WorkoutProgram,
    definition: TemplateDefinition,
    user: User,
    advisories: list[Advisory] | None = None,
) -> ProgramPreviewOut:
    exercise_ids = [ex.exercise_id for w in program.workouts for ex in w.exercises]
    exercises = await get_exercises_by_ids(db, exercise_ids) if exercise_ids else {}

    current_week: int | None = None
    if program.status == ProgramStatus.ACTIVE and program.start_date is not None:
        elapsed_week = (date.today() - program.start_date).days // 7 + 1
        current_week = elapsed_week if 1 <= elapsed_week <= program.duration_weeks else None

    set_logs_by_exercise: dict[int, list[WorkoutSetLog]] | None = None
    readiness_logs: list[UserWorkoutLog] | None = None
    if current_week is not None:
        workout_ids = [workout.id for workout in program.workouts]
        set_logs_by_exercise = {}
        for workout in program.workouts:
            for log in await get_set_logs(db, workout.id, user.id):
                set_logs_by_exercise.setdefault(log.workout_exercise_id, []).append(log)
        since = date.today() - timedelta(days=DELOAD_LOOKBACK_DAYS)
        readiness_logs = await get_workout_logs_for_workouts(db, workout_ids, user.id, since)

    weeks = {
        w: [
            WorkoutPreviewOut(**day)
            for day in derive_week(
                program,
                definition,
                w,
                exercises,
                set_logs_by_exercise=set_logs_by_exercise if w == current_week else None,
                readiness_logs=readiness_logs if w == current_week else None,
            )
        ]
        for w in range(1, program.duration_weeks + 1)
    }
    return ProgramPreviewOut(
        program_id=program.id,
        name=program.name,
        status=program.status.value,
        duration_weeks=program.duration_weeks,
        weeks=weeks,
        advisories=advisories or [],
    )
```

- [ ] **Step 4: Update every call site to pass `user`**

In `draft()`:
```python
    return await _preview_out(db, saved, preview_definition, user, advisories=advisory_sink)
```

In `get_active()`:
```python
    return await _preview_out(db, program, definition, user)
```

In `get_one()`:
```python
    return await _preview_out(db, program, definition, user)
```

In `preview()`:
```python
    return await _preview_out(db, program, definition, user)
```

In `feedback()`:
```python
    return await _preview_out(db, saved, definition, user)
```

In `accept()`:
```python
    return await _preview_out(db, program, definition, user)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose exec backend pytest tests/test_programs_live_signals.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `docker-compose exec backend pytest`
Expected: all PASS — this confirms the `_preview_out` signature change didn't break `test_programs_flow.py`, `test_telemetry_endpoints.py`, or any other caller.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/endpoints/programs.py backend/tests/test_programs_live_signals.py
git commit -m "feat(backend): wire live autoregulation/deload signals into the current active week"
```

---

## Task 5: Add a start-date field to the program-creation wizard

**Files:**
- Modify: `frontend/src/types/programCreation.ts` (`MatchRequest`, line 82)
- Modify: `frontend/src/components/ProgramWizardStep1.tsx`
- Create: `frontend/src/tests/components/ProgramWizardStep1.test.tsx`

**Interfaces:**
- Consumes: existing `FormField` component (`type="date"` passes straight through to a native `<input>`, no changes needed there).
- Produces: `MatchRequest.start_date: string` (form-values type). Task 6 reads this off `formPrefs.start_date` in `ProgramBuilderPage.tsx`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/components/ProgramWizardStep1.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgramWizardStep1 } from '@/components/ProgramWizardStep1';

describe('ProgramWizardStep1', () => {
  it('defaults the start date to today and submits it with the form values', () => {
    const onSubmit = vi.fn();
    const today = new Date().toISOString().slice(0, 10);

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    const startDateInput = screen.getByLabelText(/start date/i) as HTMLInputElement;
    expect(startDateInput.value).toBe(today);

    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_date: today }));
  });

  it('submits a user-chosen start date', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/start date/i), { target: { value: '2026-08-10' } });
    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_date: '2026-08-10' }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npx vitest run src/tests/components/ProgramWizardStep1.test.tsx`
Expected: FAIL — `getByLabelText(/start date/i)` finds no matching element yet.

- [ ] **Step 3: Add `start_date` to the form-values type**

In `frontend/src/types/programCreation.ts`:

```ts
export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | '';
  start_date: string;
  movement_preferences?: Record<EquipmentFamily, number>;
  complementary_focus?: boolean;
  variety_preference?: VarietyPreference;
}
```

- [ ] **Step 4: Add the field to `ProgramWizardStep1`**

In `frontend/src/components/ProgramWizardStep1.tsx`, add `today` and the new state (right after the component opens, and after `sessionDurationMin`'s state declaration respectively):

```tsx
export function ProgramWizardStep1({
  environmentId,
  onSubmit,
  onCancel,
  initialValues,
}: ProgramWizardStep1Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [daysPerWeek, setDaysPerWeek] = useState(initialValues?.days_per_week.toString() ?? '3');
  const [sessionDurationMin, setSessionDurationMin] = useState(
    initialValues?.session_duration_min.toString() ?? '60',
  );
  const [startDate, setStartDate] = useState(initialValues?.start_date ?? today);
```

In the `useEffect` that syncs `initialValues`, add alongside the other unconditional setters:

```tsx
  useEffect(() => {
    if (initialValues) {
      setDaysPerWeek(initialValues.days_per_week.toString());
      setSessionDurationMin(initialValues.session_duration_min.toString());
      setStartDate(initialValues.start_date);
      setWeightUnit(initialValues.weight_unit);
```

In `handleSubmit`'s payload:

```tsx
    onSubmit({
      environment_id: environmentId,
      days_per_week: parseInt(daysPerWeek, 10),
      session_duration_min: parseInt(sessionDurationMin, 10),
      start_date: startDate,
      weight_unit: weightUnit,
      progression_style: progressionStyle,
      effort_method: effortMethod,
      movement_preferences: movementPreferences,
      complementary_focus: complementaryFocus,
      variety_preference: varietyPreference,
    });
```

Add the field to the JSX, right after the "Session Duration" `FormField` and before the "Weight Unit" `<div className="input-group">`:

```tsx
        {/* Start Date */}
        <FormField
          label="Start Date"
          type="date"
          name="start_date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          min={today}
          required
        />
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec frontend npx vitest run src/tests/components/ProgramWizardStep1.test.tsx`
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/programCreation.ts frontend/src/components/ProgramWizardStep1.tsx frontend/src/tests/components/ProgramWizardStep1.test.tsx
git commit -m "feat(frontend): collect a start date in the program-creation wizard"
```

---

## Task 6: Thread `start_date` into the draft request

**Files:**
- Modify: `frontend/src/types/program.ts` (`DraftRequest`, line 94)
- Modify: `frontend/src/pages/ProgramBuilderPage.tsx` (`makeDraft`)
- Modify: `frontend/src/tests/pages/ProgramBuilderPage.test.tsx`

**Interfaces:**
- Consumes: `formPrefs.start_date` (produced by Task 5's `MatchRequest.start_date`), existing `createDraft.mutateAsync(req: DraftRequest)` (`frontend/src/hooks/usePrograms.ts:108`, unchanged).
- Produces: `DraftRequest.start_date: string` — the last field this feature needs; `createDraft`'s request body now always includes a real `start_date`, satisfying backend Task 1's now-required `DraftRequest.start_date`.

- [ ] **Step 1: Write the failing test**

In `frontend/src/tests/pages/ProgramBuilderPage.test.tsx`, the shared `ProgramWizard` mock at the top of the file must also hand back `start_date` (its `onComplete` payload is typed as `MatchRequest`, which now requires it after Task 5 — otherwise this file fails `npm run type-check`). Update the mock:

```tsx
vi.mock('@/components/ProgramWizard', () => ({
  ProgramWizard: ({
    environmentId,
    onComplete,
  }: {
    environmentId: number;
    onComplete: (values: MatchRequest) => void;
  }) => (
    <button
      onClick={() =>
        onComplete({
          environment_id: environmentId,
          days_per_week: 3,
          session_duration_min: 60,
          weight_unit: 'kg',
          progression_style: 'consistent',
          effort_method: '',
          start_date: '2026-08-01',
          movement_preferences: {
            dumbbells: 50,
            barbells: 50,
            machines: 50,
            bodyweight: 50,
            cables: 50,
            kettlebells: 50,
          },
          complementary_focus: true,
          variety_preference: 'low',
        })
      }
    >
      Submit prefs
    </button>
  ),
}));
```

Add a new test (near the other `Details step skip UX` tests, inside `describe('ProgramBuilderPage', ...)`):

```tsx
  it('includes the chosen start_date in the draft request payload', async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
      userProfile: { id: 1, fitness_focus: 'strength', age: 30, gender: 'male' },
      isAuthenticated: true,
      isLoading: false,
      setAuth: vi.fn(),
      setUserProfile: vi.fn(),
      clearAuth: vi.fn(),
      setLoading: vi.fn(),
    });

    vi.mocked(programsApi.matchTemplates).mockResolvedValue(
      mockTemplateMatchResponse([
        {
          template_id: 1,
          slug: 'bodyweight-full-body-x3',
          name: 'Bodyweight Full Body',
          fit_pct: 80,
          factors: {},
          required_inputs: [],
          tier: 'best',
          all_infeasible: false,
          advisories: [],
        },
      ]),
    );
    vi.mocked(programsApi.createDraft).mockResolvedValue({
      program_id: 1,
      name: 'Bodyweight Full Body',
      status: 'draft',
      duration_weeks: 8,
      weeks: { '1': [] },
      advisories: [],
    });

    render(wrap(<ProgramBuilderPage />));
    fireEvent.click(screen.getByText('Submit prefs'));

    await waitFor(() => expect(screen.getByText('Bodyweight Full Body')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Bodyweight Full Body'));

    await waitFor(() => {
      expect(programsApi.createDraft).toHaveBeenCalledWith(
        expect.objectContaining({ start_date: '2026-08-01' }),
      );
    });
  });
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `docker-compose exec frontend npx vitest run src/tests/pages/ProgramBuilderPage.test.tsx`
Expected: the new test FAILS (`createDraft` is called without `start_date`); every pre-existing test in the file still PASSES (they use `objectContaining`, which ignores the extra `start_date` key now present in the mock's payload).

- [ ] **Step 3: Add `start_date` to `DraftRequest`**

In `frontend/src/types/program.ts`:

```ts
export interface DraftRequest extends MatchRequest {
  template_id: number;
  required_inputs: Record<string, number | string>;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | null;
  start_date: string;
}
```

(`MatchRequest` here already has `duration_weeks`/`fitness_focus`/etc.; `start_date` is inherited if added to the base interface, but the base `MatchRequest` in `program.ts` is the *API-facing* type built by `onPrefs`, not the form type from Task 5 — it does not go through the wizard, so add it directly on `DraftRequest` as shown above rather than on `program.ts`'s `MatchRequest`.)

- [ ] **Step 4: Pass `formPrefs.start_date` through `makeDraft`**

In `frontend/src/pages/ProgramBuilderPage.tsx`:

```tsx
  const makeDraft = async (m: TemplateMatch, requiredInputs: Record<string, number | string>) => {
    if (!apiPrefs || !formPrefs) return;
    setRequiredInputValues(requiredInputs);
    const program = await createDraft.mutateAsync({
      ...apiPrefs,
      template_id: m.template_id,
      required_inputs: requiredInputs,
      progression_style: formPrefs.progression_style,
      effort_method: formPrefs.effort_method || null,
      start_date: formPrefs.start_date,
    });
    setDraft(program);
    setStep(3);
  };
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose exec frontend npx vitest run src/tests/pages/ProgramBuilderPage.test.tsx`
Expected: all PASS.

- [ ] **Step 6: Run the full frontend check**

Run: `docker-compose exec frontend npm run type-check && docker-compose exec frontend npm run test -- run`
Expected: no TypeScript errors, full test suite PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/program.ts frontend/src/pages/ProgramBuilderPage.tsx frontend/src/tests/pages/ProgramBuilderPage.test.tsx
git commit -m "feat(frontend): send the chosen start_date when creating a draft program"
```

---

## Manual Verification (after Task 6)

No dedicated manual QA beyond confirming the new date field renders and submits correctly in the wizard (the banner/reason rendering itself was already manually verified in the prior plan — see `docs/superpowers/specs/2026-07-26-adjustment-reason-banner-design.md`):

1. `docker-compose up`, log in, start the program-creation wizard.
2. Confirm the "Start Date" field appears in the Preferences step, defaults to today, and can be changed.
3. Complete the wizard, accept the resulting program.
4. Manually backdate that program's `start_date` by ~2 weeks and log a couple of high-RPE sets / low-readiness check-ins against one of its workouts (via the API or DB), then reload the workout-tracking page and confirm the adjustment/deload banner now appears — proving the wiring reaches the already-built frontend banner from the prior plan.
