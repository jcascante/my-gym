# Free-Order Workout Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user log any set of any exercise in a workout in any order, correct a set that's already logged, and control which exercise sections are expanded, instead of being forced through a one-exercise-at-a-time wizard.

**Architecture:** Backend drops the DB constraint that blocks re-logging a set and adds dedupe-on-read (highest `id` wins per set) everywhere set logs are read. Frontend replaces the single "current exercise" pointer in `useSessionProgress` with per-exercise progress for every slot at once, and replaces the single `SetLogger`/`CompletedSets` pairing with a `SetRow` (per-set, two display states) nested inside a collapsible `ExerciseSection` (one per slot).

**Tech Stack:** FastAPI + SQLAlchemy (async) + Alembic on the backend; React + TypeScript + Vitest/Testing Library on the frontend.

## Global Constraints

- `WorkoutSetLog` stays insert-only — never `UPDATE` an existing row. (spec: Approach)
- Dedupe-on-read: the highest `id` per `(workout_exercise_id, set_number)` is the authoritative value; older rows stay in the table for audit but are never surfaced. (spec: Approach, Backend Changes)
- No changes to the `POST /sessions/{id}/set-logs` route signature or its request/response shape — it already just calls `append_set_log`. (spec: Backend Changes)
- Section open/closed state is UI-only (`useState`), seeded once per session to "first incomplete exercise open, rest collapsed," never persisted. (spec: Approach, UI Components)
- Any set can be logged directly, in any order, across any exercise; a logged set can be tapped to correct it. (spec: Approach, UI Components)
- "Complete Workout" is always enabled; if any set is unlogged, confirm before completing. If everything is logged, complete immediately. (spec: UI Components)
- Pre/post readiness modal flow (`ReadinessModal`, `postSessionReadiness`, `completeSession`) is unchanged. (spec: UI Components)

---

## Phase 1: Backend

### Task 1: Drop the per-set uniqueness constraint

**Files:**
- Modify: `backend/app/models/logging.py`
- Create: `backend/alembic/versions/c3d9f7a1b5e8_drop_unique_set_number_per_session_exercise.py`

**Interfaces:**
- Produces: `workout_set_logs` table with no unique constraint on `(session_id, workout_exercise_id, set_number)` — a second `INSERT` for the same set now succeeds instead of raising an `IntegrityError`. Later tasks (2-4) rely on this.

- [ ] **Step 1: Remove the constraint from the model**

In `backend/app/models/logging.py`, remove the `__table_args__` tuple (and the now-unused `UniqueConstraint` import) from `WorkoutSetLog`:

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    pass


class UserWorkoutLog(Base):
    """
    Immutable session-level workout log.
    Created once per workout session start; tracks readiness + completion notes.
    """

    __tablename__ = "user_workout_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), nullable=False, index=True)
    session_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    readiness: Mapped[int | None] = mapped_column(Integer)  # 1-5 scale, nullable if not provided
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class WorkoutSetLog(Base):
    """
    Immutable per-set performance log.
    Appended during/after each completed set; tracks actual weight, reps, RPE.
    A correction is a second row for the same set, not an update - readers
    (get_set_logs, get_set_logs_for_sessions, get_set_logs_for_session) dedupe to
    the highest id per (workout_exercise_id, set_number).
    """

    __tablename__ = "workout_set_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    workout_exercise_id: Mapped[int] = mapped_column(ForeignKey("workout_exercises.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), nullable=False, index=True)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_weight: Mapped[float | None] = mapped_column(Float)
    actual_reps: Mapped[int | None] = mapped_column(Integer)
    actual_rpe: Mapped[float | None] = mapped_column(Float)  # range depends on effort_method
    effort_method: Mapped[str] = mapped_column(String(20), default="rpe", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
```

- [ ] **Step 2: Write the Alembic migration**

Current head is `b6e4f9a1c7d2` (the migration that originally added this constraint). Create `backend/alembic/versions/c3d9f7a1b5e8_drop_unique_set_number_per_session_exercise.py`:

```python
"""drop unique set number per session exercise

Revision ID: c3d9f7a1b5e8
Revises: b6e4f9a1c7d2
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3d9f7a1b5e8"
down_revision: Union[str, None] = "b6e4f9a1c7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_workout_set_log_session_exercise_set", "workout_set_logs", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_workout_set_log_session_exercise_set",
        "workout_set_logs",
        ["session_id", "workout_exercise_id", "set_number"],
    )
```

- [ ] **Step 3: Verify upgrade and downgrade against the real database**

This project's test suite builds its schema straight from the SQLAlchemy models (`Base.metadata.create_all`), not from Alembic migrations, so there's no existing pytest harness for migration up/down — verify manually against the Postgres container instead, per `CLAUDE.md`'s "always test up/down":

```bash
docker-compose up -d postgres backend
docker-compose exec backend alembic upgrade head
docker-compose exec postgres psql -U postgres -d app_db -c "\d workout_set_logs"
```

Expected: the `Indexes` section does NOT list `uq_workout_set_log_session_exercise_set`.

```bash
docker-compose exec backend alembic downgrade -1
docker-compose exec postgres psql -U postgres -d app_db -c "\d workout_set_logs"
```

Expected: the `Indexes` section DOES list `uq_workout_set_log_session_exercise_set` again (as a unique constraint).

```bash
docker-compose exec backend alembic upgrade head
```

Leave the database at head before continuing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/logging.py backend/alembic/versions/c3d9f7a1b5e8_drop_unique_set_number_per_session_exercise.py
git commit -m "feat(logging): drop the per-set uniqueness constraint"
```

---

### Task 2: Dedupe-on-read for the existing set-log queries

**Files:**
- Modify: `backend/app/crud/logging.py`
- Test: `backend/tests/test_logging.py`

**Interfaces:**
- Consumes: `WorkoutSetLog` model from Task 1 (no constraint, so duplicate `set_number` rows can now exist).
- Produces: `_dedupe_latest_per_set(logs: list[WorkoutSetLog]) -> list[WorkoutSetLog]` — used by this task's two functions and by Task 3's new function.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_logging.py` (needs `from sqlalchemy import select` and `from app.models.logging import WorkoutSetLog` added to the existing imports at the top of the file):

```python
@pytest.mark.asyncio
async def test_get_set_logs_dedupes_a_corrected_set(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple, test_session: WorkoutSession
):
    """A second append for the same set is a correction - get_set_logs must surface
    only the latest value, while the original row stays in the table for audit."""
    _, workout, exercise = test_program_with_workout

    original = SessionSetLogCreate(
        workout_exercise_id=exercise.id, set_number=1, actual_weight=60.0, actual_reps=10, actual_rpe=7.0
    )
    await crud_logging.append_set_log(db_session, test_user.id, test_session, original)

    corrected = SessionSetLogCreate(
        workout_exercise_id=exercise.id, set_number=1, actual_weight=65.0, actual_reps=9, actual_rpe=8.0
    )
    await crud_logging.append_set_log(db_session, test_user.id, test_session, corrected)

    logs = await crud_logging.get_set_logs(db_session, workout.id, test_user.id)

    assert len(logs) == 1
    assert logs[0].actual_weight == 65.0
    assert logs[0].actual_reps == 9

    all_rows = (await db_session.execute(select(WorkoutSetLog))).scalars().all()
    assert len(all_rows) == 2


@pytest.mark.asyncio
async def test_get_set_logs_for_sessions_dedupes_a_corrected_set(
    db_session: AsyncSession, test_user: User, test_program_with_workout: tuple, test_session: WorkoutSession
):
    """Same dedupe guarantee for the program-scoped query used by reactive deload."""
    from datetime import timedelta

    program, _, exercise = test_program_with_workout

    original = SessionSetLogCreate(
        workout_exercise_id=exercise.id, set_number=1, actual_weight=60.0, actual_reps=10, actual_rpe=7.0
    )
    await crud_logging.append_set_log(db_session, test_user.id, test_session, original)

    corrected = SessionSetLogCreate(
        workout_exercise_id=exercise.id, set_number=1, actual_weight=65.0, actual_reps=9, actual_rpe=8.0
    )
    await crud_logging.append_set_log(db_session, test_user.id, test_session, corrected)

    logs = await crud_logging.get_set_logs_for_sessions(
        db_session, program.id, test_user.id, since=date.today() - timedelta(days=1)
    )

    assert len(logs) == 1
    assert logs[0].actual_weight == 65.0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
docker-compose exec backend pytest tests/test_logging.py -k dedupe -v
```

Expected: FAIL — both tests report `len(logs) == 2`, not `1` (no dedupe exists yet).

- [ ] **Step 3: Add the dedupe helper and apply it**

In `backend/app/crud/logging.py`, add the helper near the top (after imports) and use it in both query functions:

```python
def _dedupe_latest_per_set(logs: list[WorkoutSetLog]) -> list[WorkoutSetLog]:
    """Keep only the highest-id row per (workout_exercise_id, set_number).

    A correction is a second insert for the same set, so the highest id is always
    the current value; older rows stay in the table for audit but are never
    surfaced. Relies on dict insertion order to preserve each query's own
    ORDER BY - the first time a key is seen fixes its position, and overwriting
    the value for that key later doesn't move it.
    """
    best: dict[tuple[int, int], WorkoutSetLog] = {}
    for log in logs:
        key = (log.workout_exercise_id, log.set_number)
        current = best.get(key)
        if current is None or log.id > current.id:
            best[key] = log
    return list(best.values())
```

Update `get_set_logs`:

```python
async def get_set_logs(db: AsyncSession, workout_id: int, user_id: int) -> list[WorkoutSetLog]:
    """Get all set logs for a workout session, ordered by set_number, deduped to the latest value per set."""
    stmt = (
        select(WorkoutSetLog)
        .where(
            and_(
                WorkoutSetLog.workout_id == workout_id,
                WorkoutSetLog.user_id == user_id,
            )
        )
        .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))
```

Update `get_set_logs_for_sessions`:

```python
async def get_set_logs_for_sessions(
    db: AsyncSession, program_id: int, user_id: int, since: date
) -> list[WorkoutSetLog]:
    """Set logs for one program's sessions, windowed to the reactive-deload lookback,
    deduped to the latest value per set.

    Joining through workout_sessions is what scopes this to a single program -
    workout_id alone is shared across every week of the program that owns it.
    """
    stmt = (
        select(WorkoutSetLog)
        .join(WorkoutSession, WorkoutSession.id == WorkoutSetLog.session_id)
        .where(
            and_(
                WorkoutSession.program_id == program_id,
                WorkoutSetLog.user_id == user_id,
                WorkoutSetLog.created_at >= since,
            )
        )
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
docker-compose exec backend pytest tests/test_logging.py -v
```

Expected: PASS — all tests in the file, including the two new ones and the pre-existing `test_get_set_logs` (which has no duplicates, so dedupe is a no-op for it).

- [ ] **Step 5: Commit**

```bash
git add backend/app/crud/logging.py backend/tests/test_logging.py
git commit -m "feat(logging): dedupe set-log reads to the latest value per set"
```

---

### Task 3: Extract and dedupe the session-detail set-log query

**Files:**
- Modify: `backend/app/crud/logging.py`
- Modify: `backend/app/api/v1/endpoints/sessions.py`

**Interfaces:**
- Consumes: `_dedupe_latest_per_set` from Task 2.
- Produces: `get_set_logs_for_session(db, session_id, user_id) -> list[WorkoutSetLog]` in `app/crud/logging.py` — this is the function that feeds `SessionDetailOut.logged_sets`, which the frontend's `useSessionProgress` consumes directly. Task 4's integration test and the whole frontend phase depend on this being deduped.

This is the most important read path for the feature: `_session_detail` in `sessions.py` currently builds `logged_sets` from its own inline query (not through `get_set_logs`/`get_set_logs_for_sessions`), so Task 2 alone would leave this one path still returning duplicate rows to the frontend.

- [ ] **Step 1: Add the new crud function**

Append to `backend/app/crud/logging.py`:

```python
async def get_set_logs_for_session(db: AsyncSession, session_id: int, user_id: int) -> list[WorkoutSetLog]:
    """Set logs for a single session, deduped to the latest value per set.

    This is what session-detail responses (and thus the frontend's logged_sets)
    are built from.
    """
    stmt = (
        select(WorkoutSetLog)
        .where(
            and_(
                WorkoutSetLog.session_id == session_id,
                WorkoutSetLog.user_id == user_id,
            )
        )
        .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
    )
    result = await db.execute(stmt)
    return _dedupe_latest_per_set(list(result.scalars().all()))
```

- [ ] **Step 2: Use it from the session-detail endpoint**

In `backend/app/api/v1/endpoints/sessions.py`, `_session_detail` currently builds `logs` with an inline query (around line 109-119):

```python
    logs = (
        (
            await db.execute(
                select(WorkoutSetLog)
                .where(WorkoutSetLog.session_id == session.id)
                .order_by(WorkoutSetLog.workout_exercise_id, WorkoutSetLog.set_number)
            )
        )
        .scalars()
        .all()
    )
```

Replace that whole block with:

```python
    logs = await crud_logging.get_set_logs_for_session(db, session.id, user.id)
```

(`crud_logging` is already imported at the top of the file as `from app.crud import logging as crud_logging`; no import changes are needed — `WorkoutSetLog` and `select` are both still used elsewhere in this file.)

- [ ] **Step 3: Run the existing session tests to confirm nothing broke**

```bash
docker-compose exec backend pytest tests/test_sessions_api.py tests/test_session_model.py -v
```

Expected: PASS — all existing tests, unchanged in behavior since no duplicates existed before this feature.

- [ ] **Step 4: Commit**

```bash
git add backend/app/crud/logging.py backend/app/api/v1/endpoints/sessions.py
git commit -m "refactor(sessions): read session detail's set logs through a deduped crud function"
```

---

### Task 4: Integration test — correcting a logged set through the API

**Files:**
- Test: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `POST /users/me/sessions/{id}/set-logs` (unchanged route) and `GET /users/me/sessions/{id}` (now backed by Task 3's `get_set_logs_for_session`).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_sessions_api.py`:

```python
@pytest.mark.asyncio
async def test_correcting_a_logged_set_updates_the_session_detail(
    authenticated_client: AsyncClient, active_program: WorkoutProgram
) -> None:
    start = date.today().isoformat()
    session_id = (await authenticated_client.get(f"/api/v1/users/me/schedule?start={start}&end={start}")).json()[0][
        "session_id"
    ]

    await authenticated_client.post(
        f"/api/v1/users/me/sessions/{session_id}/set-logs",
        json={"workout_exercise_id": 1, "set_number": 1, "actual_reps": 8, "actual_rpe": 7.0},
    )
    response = await authenticated_client.post(
        f"/api/v1/users/me/sessions/{session_id}/set-logs",
        json={"workout_exercise_id": 1, "set_number": 1, "actual_reps": 10, "actual_rpe": 9.0},
    )

    assert response.status_code == 201

    detail = await authenticated_client.get(f"/api/v1/users/me/sessions/{session_id}")
    logged = detail.json()["logged_sets"]
    assert len(logged) == 1
    assert logged[0]["actual_reps"] == 10
    assert logged[0]["actual_rpe"] == 9.0
```

- [ ] **Step 2: Run the test to verify it fails**

Temporarily this test would only fail if run against a version of the code without Tasks 1-3 — since Task 1-3 are already implemented by this point in the plan, run it to confirm it PASSES immediately (there's no meaningful "red" state to observe once earlier tasks are done; this test exists to lock in the end-to-end behavior, not to drive new production code):

```bash
docker-compose exec backend pytest tests/test_sessions_api.py -k correcting -v
```

Expected: PASS.

- [ ] **Step 3: Run the full backend test suite**

```bash
docker-compose exec backend pytest -v
```

Expected: PASS — everything, confirming Phase 1 is complete and non-regressive.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_sessions_api.py
git commit -m "test(sessions): cover correcting a logged set end-to-end"
```

---

## Phase 2: Frontend

### Task 5: Rewrite `useSessionProgress` for free-order tracking

**Files:**
- Modify: `frontend/src/hooks/useSessionProgress.ts`
- Test: `frontend/src/tests/hooks/useSessionProgress.test.tsx`

**Interfaces:**
- Consumes: `SlotPreview` (`@/types/program`), `LoggedSet` (`@/types/session`), `EffortMethod` (`@/types/programCreation`).
- Produces (used by Tasks 7 and 8):
  - `LoggedSetEntry { setNumber: number; weight?: number; reps?: number; effort?: number; effort_method?: EffortMethod; timestamp: Date }`
  - `ExerciseProgress extends SlotPreview { completedSets: LoggedSetEntry[] }`
  - `useSessionProgress(slots, loggedSets?) -> { exercises: ExerciseProgress[]; totalSets: number; completedSetsTotal: number; completedExercises: number; progressPercentage: number; recordSet: (workoutExerciseId: number, setNumber: number, data: Omit<LoggedSetEntry, 'setNumber' | 'timestamp'>) => void }`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `frontend/src/tests/hooks/useSessionProgress.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import type { SlotPreview } from '@/types/program';
import type { LoggedSet } from '@/types/session';

const loggedSet = (
  id: number,
  workoutExerciseId: number,
  setNumber: number,
  weight: number,
  reps: number,
): LoggedSet => ({
  id,
  workout_exercise_id: workoutExerciseId,
  set_number: setNumber,
  actual_weight: weight,
  actual_reps: reps,
  actual_rpe: 8,
  effort_method: 'rpe',
});

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
  it('returns every exercise up front, none logged', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2), slot(2, 'Row', 2)]),
    );

    expect(result.current.exercises.map((ex) => ex.exercise_name)).toEqual(['Bench', 'Row']);
    expect(result.current.totalSets).toBe(4);
    expect(result.current.completedSetsTotal).toBe(0);
    expect(result.current.progressPercentage).toBe(0);
  });

  it('logs a set out of order without touching other sets', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 3)]));

    act(() => {
      result.current.recordSet(1, 3, { weight: 90, reps: 6, effort: 9, effort_method: 'rpe' });
    });

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 3, weight: 90, reps: 6 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('marks an exercise complete once every set is logged, in any order', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 2)]));

    act(() => {
      result.current.recordSet(1, 2, { weight: 80, reps: 8, effort: 8, effort_method: 'rpe' });
    });
    expect(result.current.completedExercises).toBe(0);

    act(() => {
      result.current.recordSet(1, 1, { weight: 80, reps: 8, effort: 8, effort_method: 'rpe' });
    });
    expect(result.current.completedExercises).toBe(1);
    expect(result.current.progressPercentage).toBe(100);
  });

  it('overwrites a set when it is logged again (a correction)', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 1)]));

    act(() => {
      result.current.recordSet(1, 1, { weight: 80, reps: 8, effort: 7, effort_method: 'rpe' });
    });
    act(() => {
      result.current.recordSet(1, 1, { weight: 85, reps: 6, effort: 9, effort_method: 'rpe' });
    });

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 85, reps: 6, effort: 9 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('resumes already-logged sets from the server instead of starting at zero', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2)], [loggedSet(101, 1, 1, 80, 8)]),
    );

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 80, reps: 8 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('dedupes server-provided logs, keeping the highest id per set', () => {
    const { result } = renderHook(() =>
      useSessionProgress(
        [slot(1, 'Bench', 1)],
        [loggedSet(101, 1, 1, 80, 8), loggedSet(102, 1, 1, 85, 6)],
      ),
    );

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 85, reps: 6 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npm run test -- src/tests/hooks/useSessionProgress.test.tsx
```

Expected: FAIL — the current hook has no `totalSets`/`completedSetsTotal` and `recordSet`'s signature doesn't accept `(workoutExerciseId, setNumber, data)`.

- [ ] **Step 3: Rewrite the hook**

Replace the full contents of `frontend/src/hooks/useSessionProgress.ts`:

```ts
import { useState, useEffect, useCallback } from 'react';
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';
import type { LoggedSet } from '@/types/session';

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

function toEntry(log: LoggedSet): LoggedSetEntry {
  return {
    setNumber: log.set_number,
    weight: log.actual_weight ?? undefined,
    reps: log.actual_reps ?? undefined,
    effort: log.actual_rpe ?? undefined,
    effort_method: log.effort_method as EffortMethod,
    timestamp: new Date(),
  };
}

// A correction is a second POST for the same set - the backend keeps both rows for
// audit but only the highest id is current. Dedupe defensively here too in case a
// stale cache ever returns both.
function dedupeLoggedSets(loggedSets: LoggedSet[]): LoggedSet[] {
  const bestByKey = new Map<string, LoggedSet>();
  for (const log of loggedSets) {
    const key = `${log.workout_exercise_id}:${log.set_number}`;
    const current = bestByKey.get(key);
    if (!current || log.id > current.id) {
      bestByKey.set(key, log);
    }
  }
  return Array.from(bestByKey.values());
}

export function useSessionProgress(slots: SlotPreview[], loggedSets: LoggedSet[] = []) {
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);

  // Keyed on slot + logged-set content rather than either array's reference: callers
  // routinely pass freshly-built arrays each render, which would otherwise make this
  // effect "reset" every render. Serializing full slot content (not just
  // workout_exercise_id) matters because a reactive deload or an exercise swap can
  // change a slot's sets/load/exercise_id while keeping the same workout_exercise_id.
  const slotsKey = JSON.stringify({ slots, loggedSets });

  useEffect(() => {
    const deduped = dedupeLoggedSets(loggedSets);
    const seeded = slots.map((slot) => ({
      ...slot,
      completedSets: deduped
        .filter((log) => log.workout_exercise_id === slot.workout_exercise_id)
        .sort((a, b) => a.set_number - b.set_number)
        .map(toEntry),
    }));
    setExercises(seeded);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slotsKey]);

  const totalSets = exercises.reduce((sum, ex) => sum + ex.sets, 0);
  const completedSetsTotal = exercises.reduce((sum, ex) => sum + ex.completedSets.length, 0);
  const completedExercises = exercises.filter((ex) => ex.completedSets.length >= ex.sets).length;
  const progressPercentage = totalSets ? (completedSetsTotal / totalSets) * 100 : 0;

  const recordSet = useCallback(
    (
      workoutExerciseId: number,
      setNumber: number,
      data: Omit<LoggedSetEntry, 'setNumber' | 'timestamp'>,
    ) => {
      setExercises((prev) =>
        prev.map((ex) =>
          ex.workout_exercise_id === workoutExerciseId
            ? {
                ...ex,
                completedSets: [
                  ...ex.completedSets.filter((s) => s.setNumber !== setNumber),
                  { ...data, setNumber, timestamp: new Date() },
                ].sort((a, b) => a.setNumber - b.setNumber),
              }
            : ex,
        ),
      );
    },
    [],
  );

  return {
    exercises,
    totalSets,
    completedSetsTotal,
    completedExercises,
    progressPercentage,
    recordSet,
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npm run test -- src/tests/hooks/useSessionProgress.test.tsx
```

Expected: PASS — all six tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSessionProgress.ts frontend/src/tests/hooks/useSessionProgress.test.tsx
git commit -m "feat(sessions): track every exercise's progress at once, not just the current one"
```

---

### Task 6: Build the `SetRow` component

**Files:**
- Create: `frontend/src/components/SetRow.tsx`
- Test: `frontend/src/components/SetRow.test.tsx`
- Modify: `frontend/src/components/index.ts`

**Interfaces:**
- Consumes: `LoggedSetEntry` (from Task 5's `@/hooks/useSessionProgress`), `EffortMethod` (`@/types/programCreation`), `Button`/`FormField` (`./Button`, `./FormField`).
- Produces (used by Task 7): `SetRow({ setNumber, effort_method, loggedSet?, onLogSet }) -> JSX.Element` where `onLogSet: (data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod }) => Promise<void> | void`. Rejecting `onLogSet` keeps the row in its input state instead of switching to the logged summary.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/SetRow.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SetRow } from './SetRow';

describe('SetRow', () => {
  it('renders an input row with a per-set Log button when unlogged', () => {
    render(<SetRow setNumber={2} effort_method="rpe" onLogSet={vi.fn()} />);

    expect(screen.getByText('Set 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Log Set 2' })).toBeInTheDocument();
  });

  it('calls onLogSet with the entered values and shows the logged summary after success', async () => {
    const onLogSet = vi.fn().mockResolvedValue(undefined);
    render(<SetRow setNumber={1} effort_method="rpe" onLogSet={onLogSet} />);

    await userEvent.type(screen.getByLabelText(/weight/i), '185');
    await userEvent.type(screen.getByLabelText(/reps/i), '8');
    await userEvent.type(screen.getByLabelText(/rpe/i), '8.5');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    expect(onLogSet).toHaveBeenCalledWith({ weight: 185, reps: 8, effort: 8.5, effort_method: 'rpe' });
    expect(await screen.findByText(/set 1 logged, tap to edit/i)).toBeInTheDocument();
  });

  it('renders a logged summary row when a loggedSet is passed in', () => {
    render(
      <SetRow
        setNumber={1}
        effort_method="rpe"
        loggedSet={{ setNumber: 1, weight: 80, reps: 8, effort: 7, effort_method: 'rpe', timestamp: new Date() }}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText(/set 1.*80 lb.*8 reps.*rpe 7/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Log Set 1' })).not.toBeInTheDocument();
  });

  it('tapping a logged summary reopens the input, prefilled, for correction', async () => {
    const onLogSet = vi.fn().mockResolvedValue(undefined);
    render(
      <SetRow
        setNumber={1}
        effort_method="rpe"
        loggedSet={{ setNumber: 1, weight: 80, reps: 8, effort: 7, effort_method: 'rpe', timestamp: new Date() }}
        onLogSet={onLogSet}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /set 1 logged, tap to edit/i }));

    expect((screen.getByLabelText(/weight/i) as HTMLInputElement).value).toBe('80');
    expect((screen.getByLabelText(/reps/i) as HTMLInputElement).value).toBe('8');
    expect((screen.getByLabelText(/rpe/i) as HTMLInputElement).value).toBe('7');
  });

  it('stays in the input state if onLogSet rejects', async () => {
    const onLogSet = vi.fn().mockRejectedValue(new Error('network error'));
    render(<SetRow setNumber={1} effort_method="rpe" onLogSet={onLogSet} />);

    await userEvent.type(screen.getByLabelText(/rpe/i), '8');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() => expect(onLogSet).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Log Set 1' })).toBeInTheDocument();
  });

  it('clamps RPE to 1-10 range', async () => {
    render(<SetRow setNumber={1} effort_method="rpe" onLogSet={vi.fn()} />);
    const rpeInput = screen.getByLabelText(/rpe/i);
    await userEvent.type(rpeInput, '15');
    await userEvent.tab();
    expect((rpeInput as HTMLInputElement).value).toBe('10');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npm run test -- src/components/SetRow.test.tsx
```

Expected: FAIL with "Cannot find module './SetRow'" (the component doesn't exist yet).

- [ ] **Step 3: Create the component**

Create `frontend/src/components/SetRow.tsx`:

```tsx
import React, { useState } from 'react';
import { EffortMethod } from '../types/programCreation';
import { Button } from './Button';
import { FormField } from './FormField';
import type { LoggedSetEntry } from '../hooks/useSessionProgress';

interface SetRowProps {
  setNumber: number;
  effort_method: EffortMethod;
  loggedSet?: LoggedSetEntry;
  onLogSet: (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => Promise<void> | void;
}

function getEffortBounds(effort_method: EffortMethod) {
  switch (effort_method) {
    case 'rpe':
      return { min: 1, max: 10, label: 'RPE (1–10)', short: 'RPE' };
    case 'rir':
      return { min: 0, max: 10, label: 'Reps in Reserve (0–10)', short: 'RIR' };
    case 'borg':
      return { min: 6, max: 20, label: 'Borg Scale (6–20) - Perceived Exertion', short: 'Borg' };
    default:
      return { min: 1, max: 10, label: 'RPE (1–10)', short: 'RPE' };
  }
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export const SetRow: React.FC<SetRowProps> = ({ setNumber, effort_method, loggedSet, onLogSet }) => {
  const [mode, setMode] = useState<'summary' | 'edit'>(loggedSet ? 'summary' : 'edit');
  const [weight, setWeight] = useState<number | ''>(loggedSet?.weight ?? '');
  const [reps, setReps] = useState<number | ''>(loggedSet?.reps ?? '');
  const [effort, setEffort] = useState<number | ''>(loggedSet?.effort ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { min, max, label, short } = getEffortBounds(effort_method);

  const handleWeightBlur = () => {
    if (weight !== '' && weight < 0) setWeight('');
  };

  const handleRepsBlur = () => {
    if (reps !== '' && (reps < 1 || reps > 100)) setReps('');
  };

  const handleEffortBlur = () => {
    if (effort !== '') setEffort(clamp(Number(effort), min, max));
  };

  const handleEditTap = () => {
    if (!loggedSet) return;
    setWeight(loggedSet.weight ?? '');
    setReps(loggedSet.reps ?? '');
    setEffort(loggedSet.effort ?? '');
    setMode('edit');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (effort === '' || isSubmitting) return;

    const effortVal = clamp(Number(effort), min, max);

    setIsSubmitting(true);
    try {
      await onLogSet({
        weight: weight !== '' ? weight : undefined,
        reps: reps !== '' ? reps : undefined,
        effort: effortVal,
        effort_method,
      });
      setMode('summary');
    } catch {
      // Stay in edit mode with the entered values so the user can retry - the
      // caller is responsible for surfacing the failure (e.g. a toast).
    } finally {
      setIsSubmitting(false);
    }
  };

  if (mode === 'summary' && loggedSet) {
    return (
      <button
        type="button"
        onClick={handleEditTap}
        aria-label={`Set ${setNumber} logged, tap to edit`}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-success-50 dark:bg-success-900 border border-success-200 dark:border-success-700 text-left"
      >
        <span className="text-body-sm font-variant-numeric tabular-nums">
          Set {setNumber} · {loggedSet.weight ?? '—'} lb × {loggedSet.reps ?? '—'} reps
          {loggedSet.effort !== undefined ? ` · ${short} ${loggedSet.effort}` : ''}
        </span>
        <span className="text-success-600 dark:text-success-400 text-sm shrink-0">✓ tap to edit</span>
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-2 rounded-lg border border-neutral-200 dark:border-neutral-700 p-3"
    >
      <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Set {setNumber}</p>
      <div className="grid grid-cols-3 gap-2">
        <FormField
          id={`weight-input-${setNumber}`}
          label="Weight (optional)"
          type="number"
          step="0.5"
          value={weight}
          onChange={(e) => setWeight(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleWeightBlur}
          placeholder="0"
        />
        <FormField
          id={`reps-input-${setNumber}`}
          label="Reps (optional)"
          type="number"
          value={reps}
          onChange={(e) => setReps(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleRepsBlur}
          placeholder="0"
        />
        <FormField
          id={`effort-input-${setNumber}`}
          label={label}
          type="number"
          step={effort_method === 'rpe' ? 0.5 : 1}
          value={effort}
          onChange={(e) => setEffort(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleEffortBlur}
          placeholder="0"
        />
      </div>
      <Button type="submit" variant="primary" disabled={effort === '' || isSubmitting} className="w-full">
        Log Set {setNumber}
      </Button>
    </form>
  );
};
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npm run test -- src/components/SetRow.test.tsx
```

Expected: PASS — all six tests.

- [ ] **Step 5: Export it from the barrel**

In `frontend/src/components/index.ts`, add (alphabetically near the other exports, e.g. after `SessionStatusBadge`):

```ts
export { SetRow } from './SetRow';
```

(Leave the existing `SetLogger`/`CompletedSets` exports in place for now — Task 9 removes them once `WorkoutTrackingPage` no longer references them.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SetRow.tsx frontend/src/components/SetRow.test.tsx frontend/src/components/index.ts
git commit -m "feat(sessions): add SetRow, a per-set input/summary row with tap-to-edit"
```

---

### Task 7: Build the `ExerciseSection` component

**Files:**
- Create: `frontend/src/components/ExerciseSection.tsx`
- Test: `frontend/src/components/ExerciseSection.test.tsx`
- Modify: `frontend/src/components/index.ts`

**Interfaces:**
- Consumes: `ExerciseProgress`, `LoggedSetEntry` (Task 5's `@/hooks/useSessionProgress`), `SetRow` (Task 6), `formatSlotNote` (`@/utils/slotNote`).
- Produces (used by Task 8): `ExerciseSection({ exercise, effort_method, isOpen, onToggle, onLogSet }) -> JSX.Element` where `onLogSet: (setNumber: number, data: {...}) => Promise<void> | void`. The root element carries `data-testid="exercise-section-{workout_exercise_id}"`, used by Task 8's tests to scope queries when more than one section is on screen at once.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ExerciseSection.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExerciseSection } from './ExerciseSection';
import type { ExerciseProgress } from '../hooks/useSessionProgress';

const exercise = (overrides: Partial<ExerciseProgress> = {}): ExerciseProgress => ({
  workout_exercise_id: 1,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 2,
  reps: 8,
  load: 80,
  rest_seconds: 90,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
  completedSets: [],
  ...overrides,
});

describe('ExerciseSection', () => {
  it('shows the set count and hides sets when collapsed', () => {
    render(
      <ExerciseSection exercise={exercise()} effort_method="rpe" isOpen={false} onToggle={vi.fn()} onLogSet={vi.fn()} />,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText('0/2 sets')).toBeInTheDocument();
    expect(screen.queryByText('Set 1')).not.toBeInTheDocument();
  });

  it('shows a checkmark once every set is logged', () => {
    render(
      <ExerciseSection
        exercise={exercise({
          completedSets: [
            { setNumber: 1, weight: 80, reps: 8, effort: 8, effort_method: 'rpe', timestamp: new Date() },
            { setNumber: 2, weight: 80, reps: 8, effort: 8, effort_method: 'rpe', timestamp: new Date() },
          ],
        })}
        effort_method="rpe"
        isOpen={false}
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('2/2 sets')).toBeInTheDocument();
  });

  it('calls onToggle when the header is clicked', async () => {
    const onToggle = vi.fn();
    render(
      <ExerciseSection exercise={exercise()} effort_method="rpe" isOpen={false} onToggle={onToggle} onLogSet={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole('button', { name: /bench press/i }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('renders one SetRow per set, in set order, when open', () => {
    render(<ExerciseSection exercise={exercise()} effort_method="rpe" isOpen onToggle={vi.fn()} onLogSet={vi.fn()} />);

    expect(screen.getByText('Set 1')).toBeInTheDocument();
    expect(screen.getByText('Set 2')).toBeInTheDocument();
  });

  it('passes the tapped set number through to onLogSet', async () => {
    const onLogSet = vi.fn().mockResolvedValue(undefined);
    render(<ExerciseSection exercise={exercise()} effort_method="rpe" isOpen onToggle={vi.fn()} onLogSet={onLogSet} />);

    await userEvent.type(screen.getAllByLabelText('RPE (1–10)')[1], '7');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 2' }));

    expect(onLogSet).toHaveBeenCalledWith(2, { weight: undefined, reps: undefined, effort: 7, effort_method: 'rpe' });
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npm run test -- src/components/ExerciseSection.test.tsx
```

Expected: FAIL with "Cannot find module './ExerciseSection'".

- [ ] **Step 3: Create the component**

Create `frontend/src/components/ExerciseSection.tsx`:

```tsx
import React from 'react';
import { EffortMethod } from '../types/programCreation';
import { SetRow } from './SetRow';
import { formatSlotNote } from '../utils/slotNote';
import type { ExerciseProgress, LoggedSetEntry } from '../hooks/useSessionProgress';

interface ExerciseSectionProps {
  exercise: ExerciseProgress;
  effort_method: EffortMethod;
  isOpen: boolean;
  onToggle: () => void;
  onLogSet: (
    setNumber: number,
    data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod },
  ) => Promise<void> | void;
}

export const ExerciseSection: React.FC<ExerciseSectionProps> = ({
  exercise,
  effort_method,
  isOpen,
  onToggle,
  onLogSet,
}) => {
  const completedCount = exercise.completedSets.length;
  const isComplete = completedCount >= exercise.sets;
  const findSet = (setNumber: number): LoggedSetEntry | undefined =>
    exercise.completedSets.find((s) => s.setNumber === setNumber);

  return (
    <div
      data-testid={`exercise-section-${exercise.workout_exercise_id}`}
      className="border border-neutral-200 dark:border-neutral-700 rounded-lg mb-3 bg-white dark:bg-neutral-800 overflow-hidden"
    >
      <button type="button" onClick={onToggle} aria-expanded={isOpen} className="w-full flex items-center justify-between px-4 py-3">
        <span className="flex items-center gap-2 font-semibold text-neutral-900 dark:text-neutral-100">
          {isComplete && <span className="text-success-600 dark:text-success-400">✓</span>}
          {exercise.exercise_name}
        </span>
        <span className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400">
          {completedCount}/{exercise.sets} sets
          <span>{isOpen ? '▴' : '▾'}</span>
        </span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400">
            <span>
              Target: {exercise.load ?? '—'} × {exercise.reps}
            </span>
            <span>
              Rest {Math.floor(exercise.rest_seconds / 60)}:
              {String(exercise.rest_seconds % 60).padStart(2, '0')}
            </span>
          </div>

          {exercise.note && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {formatSlotNote(exercise.note)}
              {exercise.adjustment_reason ? ` — ${exercise.adjustment_reason}` : ''}
            </p>
          )}

          <div className="space-y-2">
            {Array.from({ length: exercise.sets }, (_, i) => i + 1).map((setNumber) => (
              <SetRow
                key={setNumber}
                setNumber={setNumber}
                effort_method={effort_method}
                loggedSet={findSet(setNumber)}
                onLogSet={(data) => onLogSet(setNumber, data)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npm run test -- src/components/ExerciseSection.test.tsx
```

Expected: PASS — all five tests.

- [ ] **Step 5: Export it from the barrel**

In `frontend/src/components/index.ts`, add:

```ts
export { ExerciseSection } from './ExerciseSection';
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ExerciseSection.tsx frontend/src/components/ExerciseSection.test.tsx frontend/src/components/index.ts
git commit -m "feat(sessions): add ExerciseSection, a collapsible per-exercise set list"
```

---

### Task 8: Rewrite `WorkoutTrackingPage` around collapsible sections

**Files:**
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx`
- Modify: `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx`

**Interfaces:**
- Consumes: `useSessionProgress` (Task 5), `ExerciseSection` (Task 7), `Toast`/`Button`/`ReadinessModal`/`Spinner`/`Alert` (`@/components`), `logSessionSet`/`postSessionReadiness`/`completeSession` (`@/api/sessions`, unchanged).

- [ ] **Step 1: Rewrite the page tests first**

Replace the full contents of `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';
import type { SessionDetail } from '@/types/session';

const navigateMock = vi.fn();
const completeSessionMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const logSessionSetMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const postSessionReadinessMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();

vi.mock('@/api/sessions', () => ({
  logSessionSet: (...args: unknown[]): Promise<unknown> => logSessionSetMock(...args),
  postSessionReadiness: (...args: unknown[]): Promise<unknown> => postSessionReadinessMock(...args),
  completeSession: (...args: unknown[]): Promise<unknown> => completeSessionMock(...args),
}));

const baseSlot = {
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

const slot = (overrides: Partial<typeof baseSlot>) => ({ ...baseSlot, ...overrides });

let sessionData: SessionDetail;

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({ data: sessionData, isLoading: false, error: null }),
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
    postSessionReadinessMock.mockClear().mockResolvedValue(undefined);
    sessionData = {
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
      slots: [slot({ workout_exercise_id: 3, exercise_name: 'Bench Press', sets: 1 })],
      logged_sets: [],
      completed_at: null,
      reactive_deload: false,
      deload_reason: null,
    };
  });

  it('renders every exercise as a section, first incomplete open by default', () => {
    sessionData.slots = [
      slot({ workout_exercise_id: 1, exercise_name: 'Bench Press', sets: 1 }),
      slot({ workout_exercise_id: 2, exercise_name: 'Row', sets: 1 }),
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText('Row')).toBeInTheDocument();
    expect(screen.getByText('Set 1')).toBeInTheDocument();
  });

  it('logs sets out of order across exercises without auto-advancing', async () => {
    sessionData.slots = [
      slot({ workout_exercise_id: 1, exercise_name: 'Bench Press', sets: 1 }),
      slot({ workout_exercise_id: 2, exercise_name: 'Row', sets: 1 }),
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /row/i }));

    const rowSection = within(screen.getByTestId('exercise-section-2'));
    await userEvent.type(rowSection.getByLabelText('RPE (1–10)'), '7');
    await userEvent.click(rowSection.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() =>
      expect(logSessionSetMock).toHaveBeenCalledWith(9, expect.objectContaining({ workout_exercise_id: 2 })),
    );
    // Bench Press (still open as the seeded first-incomplete section) is untouched -
    // its own "Log Set 1" button is still there, unaffected by Row's.
    const benchSection = within(screen.getByTestId('exercise-section-1'));
    expect(benchSection.getByRole('button', { name: 'Log Set 1' })).toBeInTheDocument();
  });

  it('toggles a section open and closed on header click', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Set 1')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /bench press/i }));
    expect(screen.queryByText('Set 1')).not.toBeInTheDocument();
  });

  it('lets a logged set be corrected by tapping it', async () => {
    sessionData.logged_sets = [
      { id: 1, workout_exercise_id: 3, set_number: 1, actual_weight: 80, actual_reps: 8, actual_rpe: 7, effort_method: 'rpe' },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /set 1 logged, tap to edit/i }));
    const rpeInput = screen.getByLabelText('RPE (1–10)');
    expect((rpeInput as HTMLInputElement).value).toBe('7');

    await userEvent.clear(rpeInput);
    await userEvent.type(rpeInput, '9');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() =>
      expect(logSessionSetMock).toHaveBeenCalledWith(
        9,
        expect.objectContaining({ workout_exercise_id: 3, set_number: 1, actual_rpe: 9 }),
      ),
    );
    expect(await screen.findByText(/set 1 logged, tap to edit/i)).toBeInTheDocument();
  });

  it('completes the workout immediately when every set is logged', async () => {
    sessionData.logged_sets = [
      { id: 1, workout_exercise_id: 3, set_number: 1, actual_weight: 80, actual_reps: 8, actual_rpe: 7, effort_method: 'rpe' },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    expect(screen.queryByText(/not logged/i)).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: /skip/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });

  it('confirms before completing when a set is unlogged', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    expect(await screen.findByText(/1 set is not logged/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(screen.queryByText(/how was that workout/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    await userEvent.click(screen.getByRole('button', { name: /finish anyway/i }));
    expect(await screen.findByText(/how was that workout/i)).toBeInTheDocument();
  });

  it('still completes the session if the readiness POST itself fails', async () => {
    postSessionReadinessMock.mockRejectedValue(new Error('network error'));
    sessionData.logged_sets = [
      { id: 1, workout_exercise_id: 3, set_number: 1, actual_weight: 80, actual_reps: 8, actual_rpe: 7, effort_method: 'rpe' },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });

  it('a submitted rating completes the session exactly once', async () => {
    sessionData.logged_sets = [
      { id: 1, workout_exercise_id: 3, set_number: 1, actual_weight: 80, actual_reps: 8, actual_rpe: 7, effort_method: 'rpe' },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
    expect(completeSessionMock).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
npm run test -- src/tests/pages/WorkoutTrackingPage.test.tsx
```

Expected: FAIL — the current page still renders the single-exercise wizard markup these tests don't expect.

- [ ] **Step 3: Rewrite the page**

Replace the full contents of `frontend/src/pages/WorkoutTrackingPage.tsx`:

```tsx
import { useRef, useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ExerciseSection, Toast, Button, ReadinessModal, Spinner, Alert } from '@/components';
import type { EffortMethod } from '@/types/programCreation';
import { useAuthStore } from '@/store/auth';
import { useSession } from '@/hooks/useSession';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import { logSessionSet, postSessionReadiness, completeSession } from '@/api/sessions';

export default function WorkoutTrackingPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const sessionIdNum = sessionId ? Number(sessionId) : null;
  const { data: session, isLoading, error } = useSession(sessionIdNum);
  const { userProfile } = useAuthStore();

  const rawEffortMethod = userProfile?.effort_method;
  const effortMethod: EffortMethod =
    rawEffortMethod === 'rpe' || rawEffortMethod === 'rir' || rawEffortMethod === 'borg'
      ? rawEffortMethod
      : 'rpe';

  const { exercises, totalSets, completedSetsTotal, completedExercises, progressPercentage, recordSet } =
    useSessionProgress(session?.slots ?? [], session?.logged_sets ?? []);

  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  const seededSessionRef = useRef<number | null>(null);
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);
  const [deloadBannerDismissed, setDeloadBannerDismissed] = useState(false);
  const [confirmIncomplete, setConfirmIncomplete] = useState(false);
  // Tracks whether the modal is closing as a direct result of a rating attempt
  // (success or failure) so the fallback completion path in handleReadinessClose
  // never double-fires alongside handleSubmitReadiness's own completion call.
  const ratingInFlightRef = useRef(false);

  // Seeds the open sections once per session ("first incomplete open, rest
  // collapsed") - guarded by session_id so a reload re-seeds but toggling
  // sections afterward (or logging a set) never resets the user's choices.
  useEffect(() => {
    if (!session || exercises.length === 0) return;
    if (seededSessionRef.current === session.session_id) return;
    seededSessionRef.current = session.session_id;
    const firstIncomplete = exercises.find((ex) => ex.completedSets.length < ex.sets);
    setOpenIds(new Set(firstIncomplete ? [firstIncomplete.workout_exercise_id] : []));
  }, [session, exercises]);

  if (isLoading) return <Spinner />;
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load workout: {error.message}</p>
          <Button onClick={() => navigate(-1)}>Go Back</Button>
        </div>
      </div>
    );
  }

  if (!session) return <Spinner />;

  const unloggedCount = totalSets - completedSetsTotal;

  const toggleSection = (workoutExerciseId: number) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(workoutExerciseId)) {
        next.delete(workoutExerciseId);
      } else {
        next.add(workoutExerciseId);
      }
      return next;
    });
  };

  const handleLogSet = async (
    workoutExerciseId: number,
    setNumber: number,
    data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod },
  ) => {
    if (!sessionIdNum) return;

    try {
      await logSessionSet(sessionIdNum, {
        workout_exercise_id: workoutExerciseId,
        set_number: setNumber,
        actual_weight: data.weight,
        actual_reps: data.reps,
        actual_rpe: data.effort,
        effort_method: effortMethod,
      });

      recordSet(workoutExerciseId, setNumber, {
        weight: data.weight,
        reps: data.reps,
        effort: data.effort,
        effort_method: data.effort_method,
      });

      setToast({ message: `Set ${setNumber} logged! 💪`, icon: '✓' });
    } catch (err) {
      console.error('Failed to log set:', err);
      setToast({ message: 'Failed to log set. Please try again.', icon: '⚠️' });
      throw err;
    }
  };

  const handleCompleteWorkout = () => {
    setConfirmIncomplete(false);
    ratingInFlightRef.current = false;
    setReadinessOpen('post');
  };

  const handleCompleteWorkoutClick = () => {
    if (unloggedCount > 0) {
      setConfirmIncomplete(true);
      return;
    }
    handleCompleteWorkout();
  };

  const handleSubmitReadiness = async (readiness: number) => {
    if (!sessionIdNum) return;
    ratingInFlightRef.current = true;
    const phase = readinessOpen === 'pre' ? 'pre' : 'post';

    try {
      await postSessionReadiness(sessionIdNum, readiness, phase);
      setToast({ message: `Readiness recorded: ${readiness}/5`, icon: '✓' });

      if (phase === 'post') {
        await completeSession(sessionIdNum);
        navigate('/');
      }
    } catch (err) {
      // Whether postSessionReadiness or completeSession failed, this attempt did
      // not complete the session - clear the flag so handleReadinessClose's own
      // fallback (fired next, via ReadinessModal's onClose-after-onRate) retries
      // completion instead of assuming this function already handled it.
      ratingInFlightRef.current = false;
      console.error('Failed to record readiness:', err);
      setToast({ message: 'Failed to record readiness. Please try again.', icon: '⚠️' });
    } finally {
      setReadinessOpen(null);
    }
  };

  const handleReadinessClose = async () => {
    const wasRatingAttempt = ratingInFlightRef.current;
    ratingInFlightRef.current = false;

    if (readinessOpen === 'post' && !wasRatingAttempt && sessionIdNum) {
      try {
        await completeSession(sessionIdNum);
        navigate('/');
      } catch (err) {
        console.error('Failed to complete workout:', err);
        setToast({ message: 'Failed to complete workout. Please try again.', icon: '⚠️' });
      }
    }

    setReadinessOpen(null);
  };

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mt-4 p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs text-neutral-600 dark:text-neutral-400">{session.workout_name}</p>
              <h1 className="text-2xl font-bold">
                {completedSetsTotal}/{totalSets} sets
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setReadinessOpen('pre')}
                className="px-3 py-1 text-sm bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors"
              >
                Check In
              </button>
              <button
                onClick={() => navigate(-1)}
                className="text-2xl text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setOpenIds(new Set(exercises.map((ex) => ex.workout_exercise_id)))}
              className="flex-1 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
            >
              Expand All
            </button>
            <button
              onClick={() => setOpenIds(new Set())}
              className="flex-1 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
            >
              Collapse All
            </button>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                {completedExercises}/{exercises.length} exercises
              </p>
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                {Math.round(progressPercentage)}%
              </p>
            </div>
            <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
              <div
                className="bg-primary-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 pb-24">
          {session.reactive_deload && !deloadBannerDismissed && session.deload_reason && (
            <Alert
              type="info"
              dismissible
              onDismiss={() => setDeloadBannerDismissed(true)}
              className="mb-4"
            >
              {session.deload_reason}
            </Alert>
          )}

          {exercises.map((exercise) => (
            <ExerciseSection
              key={exercise.workout_exercise_id}
              exercise={exercise}
              effort_method={effortMethod}
              isOpen={openIds.has(exercise.workout_exercise_id)}
              onToggle={() => toggleSection(exercise.workout_exercise_id)}
              onLogSet={(setNumber, data) => handleLogSet(exercise.workout_exercise_id, setNumber, data)}
            />
          ))}
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mb-4 p-4">
          <Button className="w-full" onClick={handleCompleteWorkoutClick}>
            Complete Workout
          </Button>
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          icon={toast.icon}
          variant="success"
          onClose={() => setToast(null)}
        />
      )}

      {/* Incomplete-workout confirmation */}
      {confirmIncomplete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg shadow-lg max-w-sm">
            <h2 className="text-lg font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
              Finish anyway?
            </h2>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
              {unloggedCount} {unloggedCount === 1 ? 'set is' : 'sets are'} not logged.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setConfirmIncomplete(false)}
                className="flex-1 px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteWorkout}
                className="flex-1 px-4 py-2 bg-primary-600 dark:bg-primary-700 text-white rounded hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors font-medium"
              >
                Finish anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Readiness Modal */}
      <ReadinessModal
        title={readinessOpen === 'pre' ? 'How are you feeling?' : 'How was that workout?'}
        isOpen={readinessOpen !== null}
        onRate={handleSubmitReadiness}
        onClose={handleReadinessClose}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
npm run test -- src/tests/pages/WorkoutTrackingPage.test.tsx
```

Expected: PASS — all eight tests.

- [ ] **Step 5: Run the full frontend test suite, type-check, and lint**

```bash
npm run test
npm run type-check
npm run lint
```

Expected: PASS on all three (lint may still complain about the now-unused `SetLogger`/`CompletedSets` imports if anything still references them — Task 9 removes those).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/WorkoutTrackingPage.tsx frontend/src/tests/pages/WorkoutTrackingPage.test.tsx
git commit -m "feat(sessions): drive workout tracking from collapsible, free-order exercise sections"
```

---

### Task 9: Remove `SetLogger` and `CompletedSets`

**Files:**
- Delete: `frontend/src/components/SetLogger.tsx`
- Delete: `frontend/src/components/SetLogger.test.tsx`
- Delete: `frontend/src/components/CompletedSets.tsx`
- Modify: `frontend/src/components/index.ts`

**Interfaces:** None — this task only removes now-dead code. `SetRow` (Task 6) already covers everything both components did; nothing else in the codebase imports either (`WorkoutTrackingPage` was their only consumer, rewritten in Task 8).

- [ ] **Step 1: Confirm nothing else references them**

```bash
grep -rn "SetLogger\|CompletedSets" frontend/src
```

Expected: only matches in `frontend/src/components/index.ts` (the two export lines) — no other file imports either component.

- [ ] **Step 2: Delete the files**

```bash
git rm frontend/src/components/SetLogger.tsx frontend/src/components/SetLogger.test.tsx frontend/src/components/CompletedSets.tsx
```

- [ ] **Step 3: Remove their exports**

In `frontend/src/components/index.ts`, remove these two lines:

```ts
export { SetLogger } from './SetLogger';
export { CompletedSets } from './CompletedSets';
```

- [ ] **Step 4: Run the full frontend suite, type-check, and lint**

```bash
npm run test
npm run type-check
npm run lint
```

Expected: PASS on all three, with zero references to the removed components anywhere.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/index.ts
git commit -m "chore(sessions): remove SetLogger and CompletedSets, superseded by SetRow"
```
