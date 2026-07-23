# Phase 4 Implementation Plan — Adaptive Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the workout feedback loop—users log actual RPE/reps, the engine adjusts loads reactively, and learned swap patterns refine exercise ranking.

**Architecture:** Extend `WorkoutSetLog`/`UserWorkoutLog` with frontend logging UI (4.1b–d), add autoregulation EWMA controller wrapping `model.resolve()` (4.2), reactive deload triggers (4.3), offline learning-to-rank pipeline (4.4), template/model versioning for determinism (4.5), and calibration curve (4.6).

**Tech Stack:** React 19, FastAPI, SQLAlchemy, Pydantic V2, EWMA signal processing, Bradley–Terry logistic regression (sklearn/scipy).

## Global Constraints

- **TDD:** Write tests before code; ≥80% coverage on new modules.
- **Async I/O:** All database + HTTP operations async/await.
- **Type hints:** Strict mypy on backend, TypeScript on frontend.
- **Validation:** Pydantic validators with field-level error messages.
- **Commits:** Frequent, one task per commit; include `Claude-Session` link.
- **Latency:** p95 generation < 100ms (enforced by harness suite).
- **Determinism:** Same inputs → byte-identical outputs (testable).

## File Structure

**New/Modified Files by Task:**

| Task | Files | Responsibility |
|------|-------|-----------------|
| 4.1b | `frontend/src/components/SetLogger.tsx`, `frontend/src/components/SetLogger.test.tsx` | Per-set RPE input component (respects effort_method) |
| 4.1c | `backend/app/schemas/logging.py`, `backend/app/api/v1/endpoints/logging.py`, `backend/tests/api/v1/endpoints/test_logging.py` | Readiness PATCH endpoint + schema validation |
| 4.1d | `frontend/src/pages/WorkoutTrackingPage.tsx`, tests updated | One-tap readiness prompt (1-5) pre/post-workout |
| 4.2 | `backend/app/services/progression/autoregulation.py`, `backend/app/services/program/preview.py`, `backend/tests/services/progression/test_autoregulation.py` | EWMA load adjustment + integration |
| 4.3 | `backend/app/services/progression/deload.py`, `backend/app/core/constants.py`, `backend/app/services/program/preview.py` (extend) | Reactive deload triggers |
| 4.4 | `backend/scripts/train_rank_weights.py`, `backend/tests/test_train_rank_weights.py` | Bradley–Terry learner (offline) |
| 4.5 | `backend/app/models/program.py`, Alembic migration, `backend/app/services/program/preview.py` (extend) | Template/model versioning + pinning |
| 4.6 | `backend/scripts/calibrate_score.py`, `backend/tests/test_calibrate_score.py` | Isotonic regression calibration |

---

## Task 4.1b: Frontend SetLogger Component

**Files:**
- Create: `frontend/src/components/SetLogger.tsx`
- Create: `frontend/src/components/SetLogger.test.tsx`
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx` (integrate SetLogger)

**Interfaces:**
- Consumes: `useTracking()` hook (existing, `hooks/useTracking.ts`), `UserProfile.effort_method` (existing field on user context)
- Produces: `SetLogger` React component exporting `{ onSetLogged: () => void }` callback

**Context:**
- Task 4.1a (backend POST endpoint) is in-flight via /build-feature. Wait for it to complete before testing this task's integration.
- `effort_method` enum: "RPE" | "RIR" | "Borg" (from `types/programCreation.ts`).
- RPE scale: 1–10 float (0.5-step increments).
- RIR scale: 0–10 (reps in reserve).
- Borg scale: 6–20 (perceived exertion).

---

### Step 1: Write the failing test

- [ ] Open `frontend/src/components/SetLogger.test.tsx` (create new file)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { SetLogger } from './SetLogger';

describe('SetLogger', () => {
  const mockOnSetLogged = jest.fn();

  it('renders weight, reps, and RPE inputs', () => {
    render(<SetLogger effort_method="RPE" onSetLogged={mockOnSetLogged} />);
    expect(screen.getByLabelText(/weight/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reps/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rpe/i)).toBeInTheDocument();
  });

  it('clamps RPE to 1–10 range', () => {
    render(<SetLogger effort_method="RPE" onSetLogged={mockOnSetLogged} />);
    const rpeInput = screen.getByLabelText(/rpe/i) as HTMLInputElement;
    fireEvent.change(rpeInput, { target: { value: '15' } });
    fireEvent.blur(rpeInput);
    expect(rpeInput.value).toBe('10');
  });

  it('clamps RIR to 0–10 range', () => {
    render(<SetLogger effort_method="RIR" onSetLogged={mockOnSetLogged} />);
    const rirInput = screen.getByLabelText(/reps in reserve/i) as HTMLInputElement;
    fireEvent.change(rirInput, { target: { value: '-5' } });
    fireEvent.blur(rirInput);
    expect(rirInput.value).toBe('0');
  });

  it('clamps Borg scale to 6–20', () => {
    render(<SetLogger effort_method="Borg" onSetLogged={mockOnSetLogged} />);
    const borgInput = screen.getByLabelText(/perceived exertion/i) as HTMLInputElement;
    fireEvent.change(borgInput, { target: { value: '25' } });
    fireEvent.blur(borgInput);
    expect(borgInput.value).toBe('20');
  });

  it('rejects negative weight', () => {
    render(<SetLogger effort_method="RPE" onSetLogged={mockOnSetLogged} />);
    const weightInput = screen.getByLabelText(/weight/i) as HTMLInputElement;
    fireEvent.change(weightInput, { target: { value: '-10' } });
    fireEvent.blur(weightInput);
    expect(weightInput.value).toBe('');
  });

  it('rejects reps < 1 or > 100', () => {
    render(<SetLogger effort_method="RPE" onSetLogged={mockOnSetLogged} />);
    const repsInput = screen.getByLabelText(/reps/i) as HTMLInputElement;
    fireEvent.change(repsInput, { target: { value: '101' } });
    fireEvent.blur(repsInput);
    expect(repsInput.value).toBe('');
  });

  it('calls onSetLogged with valid input on submit', async () => {
    render(<SetLogger effort_method="RPE" onSetLogged={mockOnSetLogged} />);
    const weightInput = screen.getByLabelText(/weight/i) as HTMLInputElement;
    const repsInput = screen.getByLabelText(/reps/i) as HTMLInputElement;
    const rpeInput = screen.getByLabelText(/rpe/i) as HTMLInputElement;
    const submitBtn = screen.getByRole('button', { name: /log set/i });

    fireEvent.change(weightInput, { target: { value: '185' } });
    fireEvent.change(repsInput, { target: { value: '8' } });
    fireEvent.change(rpeInput, { target: { value: '8.5' } });
    fireEvent.click(submitBtn);

    expect(mockOnSetLogged).toHaveBeenCalledWith({
      weight: 185,
      reps: 8,
      effort: 8.5,
      effort_method: 'RPE',
    });
  });
});
```

Run: `cd frontend && npm run test -- SetLogger.test.tsx`
Expected: FAIL — component does not exist.

---

### Step 2: Implement SetLogger component

- [ ] Create `frontend/src/components/SetLogger.tsx`

```typescript
import React, { useState } from 'react';

export type EffortMethod = 'RPE' | 'RIR' | 'Borg';

interface SetLoggerProps {
  effort_method: EffortMethod;
  onSetLogged: (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => void;
}

export const SetLogger: React.FC<SetLoggerProps> = ({
  effort_method,
  onSetLogged,
}) => {
  const [weight, setWeight] = useState<number | ''>('');
  const [reps, setReps] = useState<number | ''>('');
  const [effort, setEffort] = useState<number | ''>('');

  const getEffortBounds = () => {
    switch (effort_method) {
      case 'RPE':
        return { min: 1, max: 10, label: 'RPE (1–10)' };
      case 'RIR':
        return { min: 0, max: 10, label: 'Reps in Reserve (0–10)' };
      case 'Borg':
        return { min: 6, max: 20, label: 'Borg Scale (6–20)' };
    }
  };

  const clamp = (value: number, min: number, max: number) =>
    Math.max(min, Math.min(max, value));

  const handleWeightBlur = () => {
    if (weight !== '' && weight < 0) setWeight('');
  };

  const handleRepsBlur = () => {
    if (reps !== '' && (reps < 1 || reps > 100)) setReps('');
  };

  const handleEffortBlur = () => {
    if (effort !== '') {
      const { min, max } = getEffortBounds();
      setEffort(clamp(Number(effort), min, max));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (effort === '') return;

    const { min, max } = getEffortBounds();
    const effortVal = clamp(Number(effort), min, max);

    onSetLogged({
      weight: weight !== '' ? weight : undefined,
      reps: reps !== '' ? reps : undefined,
      effort: effortVal,
      effort_method,
    });

    // Reset form
    setWeight('');
    setReps('');
    setEffort('');
  };

  const { label } = getEffortBounds();

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="weight-input" className="block text-sm font-medium">
          Weight (optional)
        </label>
        <input
          id="weight-input"
          type="number"
          step="0.5"
          value={weight}
          onChange={(e) => setWeight(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleWeightBlur}
          placeholder="0"
          className="border px-2 py-1 rounded"
        />
      </div>

      <div>
        <label htmlFor="reps-input" className="block text-sm font-medium">
          Reps (optional)
        </label>
        <input
          id="reps-input"
          type="number"
          value={reps}
          onChange={(e) => setReps(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleRepsBlur}
          placeholder="0"
          className="border px-2 py-1 rounded"
        />
      </div>

      <div>
        <label htmlFor="effort-input" className="block text-sm font-medium">
          {label}
        </label>
        <input
          id="effort-input"
          type="number"
          step={effort_method === 'RPE' ? 0.5 : 1}
          value={effort}
          onChange={(e) => setEffort(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleEffortBlur}
          placeholder="0"
          className="border px-2 py-1 rounded"
        />
      </div>

      <button
        type="submit"
        disabled={effort === ''}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
      >
        Log Set
      </button>
    </form>
  );
```

---

### Step 3: Run tests to verify they pass

- [ ] Run: `cd frontend && npm run test -- SetLogger.test.tsx`
Expected: PASS (all 7 tests).

---

### Step 4: Integrate SetLogger into WorkoutTrackingPage

- [ ] Open `frontend/src/pages/WorkoutTrackingPage.tsx`

Find the section where sets are logged (likely a loop over `currentWorkout.exercises[i].sets`) and add the SetLogger component. Example integration:

```typescript
import { SetLogger } from '../components/SetLogger';

// Inside the exercise rendering loop:
<div key={`${workoutExerciseId}`} className="border p-4 rounded mb-4">
  <h3>{exercise.name}</h3>
  {/* existing set log display */}
  <SetLogger
    effort_method={userProfile.effort_method}
    onSetLogged={async (data) => {
      await logSet({
        workout_id: currentWorkout.id,
        workout_exercise_id: workoutExerciseId,
        set_number: nextSetNumber,
        actual_weight: data.weight,
        actual_reps: data.reps,
        actual_rpe: data.effort,
      });
    }}
  />
</div>
```

---

### Step 5: Run full frontend test suite

- [ ] Run: `cd frontend && npm run test`
Expected: PASS (all tests including SetLogger and updated WorkoutTrackingPage tests).

- [ ] Run: `cd frontend && npm run type-check`
Expected: PASS (no TypeScript errors).

---

### Step 6: Commit

- [ ] Stage and commit:

```bash
git add frontend/src/components/SetLogger.tsx frontend/src/components/SetLogger.test.tsx frontend/src/pages/WorkoutTrackingPage.tsx
git commit -m "feat(frontend): add SetLogger component for per-set RPE/RIR/Borg logging

- Per-set effort input respecting user's effort_method
- Validates weight >= 0, reps 1-100, effort within scale bounds
- Integrates into WorkoutTrackingPage
- Tests: 7 unit tests covering input validation and clamping

Claude-Session: https://claude.ai/code/session_01R61M9QX1crhxixZH3f3bpu"
```

---

## Task 4.1c: Readiness Endpoint (PATCH)

**Files:**
- Modify: `backend/app/schemas/logging.py` (extend from 4.1a)
- Modify: `backend/app/api/v1/endpoints/logging.py` (add PATCH endpoint)
- Modify: `backend/tests/api/v1/endpoints/test_logging.py` (add readiness tests)

**Interfaces:**
- Consumes: `UserWorkoutLog` model (existing, from task 4.1a), `get_current_user` dependency
- Produces: `PATCH /api/v1/users/me/workouts/{workout_id}/readiness` endpoint

---

### Step 1: Add readiness schema to logging.py

- [ ] Open `backend/app/schemas/logging.py` (created in 4.1a)

Add this after existing schemas:

```python
from pydantic import BaseModel, Field

class UserWorkoutLogUpdate(BaseModel):
    """Update session readiness (1-5 scale)."""
    readiness: int = Field(..., ge=1, le=5, description="Readiness 1-5 scale")

    class Config:
        json_schema_extra = {
            "example": {
                "readiness": 4,
            }
        }

class UserWorkoutLogOut(BaseModel):
    """Read session readiness and metadata."""
    id: int
    user_id: int
    workout_id: int
    readiness: int | None
    session_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### Step 2: Add PATCH endpoint to logging.py

- [ ] Open `backend/app/api/v1/endpoints/logging.py` (exists from 4.1a)

Add this endpoint:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logging import UserWorkoutLog
from app.models.program import Workout
from app.schemas.logging import UserWorkoutLogUpdate, UserWorkoutLogOut
from app.core.database import get_db
from app.core.security import get_current_user
from app.crud.logging import get_user_workout_log, update_user_workout_log
from app.models.user import User

router = APIRouter()

@router.patch(
    "/users/me/workouts/{workout_id}/readiness",
    response_model=UserWorkoutLogOut,
    status_code=status.HTTP_200_OK,
)
async def update_workout_readiness(
    workout_id: int,
    payload: UserWorkoutLogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWorkoutLogOut:
    """
    Update session readiness (1-5 scale).
    Upserts UserWorkoutLog.readiness for the given workout.
    """
    # Verify user owns the workout
    workout = await db.get(Workout, workout_id)
    if not workout or workout.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    # Get or create session log
    session_log = await get_user_workout_log(db, current_user.id, workout_id)
    if not session_log:
        # Create if doesn't exist
        session_log = UserWorkoutLog(
            user_id=current_user.id,
            workout_id=workout_id,
            session_date=datetime.utcnow(),
        )
        db.add(session_log)

    # Update readiness
    session_log.readiness = payload.readiness
    await db.commit()
    await db.refresh(session_log)
    return UserWorkoutLogOut.from_orm(session_log)
```

---

### Step 3: Add CRUD helper (if not present from 4.1a)

- [ ] Open `backend/app/crud/logging.py` (create if missing)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.logging import UserWorkoutLog

async def get_user_workout_log(
    db: AsyncSession, user_id: int, workout_id: int
) -> UserWorkoutLog | None:
    """Fetch session log by user and workout ID."""
    result = await db.execute(
        select(UserWorkoutLog).where(
            (UserWorkoutLog.user_id == user_id) &
            (UserWorkoutLog.workout_id == workout_id)
        )
    )
    return result.scalars().first()

async def update_user_workout_log(
    db: AsyncSession, user_id: int, workout_id: int, readiness: int
) -> UserWorkoutLog:
    """Update or create session log with readiness."""
    log = await get_user_workout_log(db, user_id, workout_id)
    if not log:
        log = UserWorkoutLog(
            user_id=user_id,
            workout_id=workout_id,
            session_date=datetime.utcnow(),
        )
        db.add(log)
    log.readiness = readiness
    await db.commit()
    await db.refresh(log)
    return log
```

---

### Step 4: Add tests to test_logging.py

- [ ] Open `backend/tests/api/v1/endpoints/test_logging.py` (add to file from 4.1a)

```python
import pytest
from httpx import AsyncClient
from datetime import datetime

from app.models.user import User
from app.models.program import Workout
from app.models.logging import UserWorkoutLog
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_patch_readiness_success(
    client: AsyncClient, db_session, auth_user: User
):
    """PATCH readiness updates session log."""
    # Create a workout
    workout = Workout(
        user_id=auth_user.id,
        scheduled_date=datetime.utcnow().date(),
        completed_at=None,
    )
    db_session.add(workout)
    await db_session.commit()
    await db_session.refresh(workout)

    token = create_access_token(auth_user.id)
    response = await client.patch(
        f"/api/v1/users/me/workouts/{workout.id}/readiness",
        json={"readiness": 4},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["readiness"] == 4
    assert data["workout_id"] == workout.id

@pytest.mark.asyncio
async def test_patch_readiness_invalid_scale(
    client: AsyncClient, db_session, auth_user: User
):
    """PATCH readiness rejects invalid scale."""
    workout = Workout(
        user_id=auth_user.id,
        scheduled_date=datetime.utcnow().date(),
    )
    db_session.add(workout)
    await db_session.commit()
    await db_session.refresh(workout)

    token = create_access_token(auth_user.id)
    response = await client.patch(
        f"/api/v1/users/me/workouts/{workout.id}/readiness",
        json={"readiness": 6},  # Invalid (> 5)
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_patch_readiness_not_found(
    client: AsyncClient, auth_user: User
):
    """PATCH readiness on non-existent workout returns 404."""
    token = create_access_token(auth_user.id)
    response = await client.patch(
        "/api/v1/users/me/workouts/9999/readiness",
        json={"readiness": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
```

---

### Step 5: Run backend tests

- [ ] Run: `docker-compose exec backend pytest backend/tests/api/v1/endpoints/test_logging.py -v`
Expected: PASS (all readiness tests + existing 4.1a tests).

- [ ] Run: `docker-compose exec backend mypy app/`
Expected: PASS (no type errors).

---

### Step 6: Commit

- [ ] Stage and commit:

```bash
git add backend/app/schemas/logging.py backend/app/api/v1/endpoints/logging.py backend/app/crud/logging.py backend/tests/api/v1/endpoints/test_logging.py
git commit -m "feat(backend): add PATCH endpoint for workout session readiness

- POST /api/v1/users/me/workouts/{workout_id}/readiness
- Readiness scale 1-5, Pydantic validation
- Upserts UserWorkoutLog row per session
- Tests: valid range, invalid scale, not-found cases

Claude-Session: https://claude.ai/code/session_01R61M9QX1crhxixZH3f3bpu"
```

---

## Task 4.1d: Frontend Readiness Prompt

**Files:**
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx`
- Modify: `frontend/src/pages/WorkoutTrackingPage.test.tsx`

**Interfaces:**
- Consumes: PATCH endpoint from 4.1c
- Produces: Readiness 1-5 input UI (one-tap modal pre/post-workout)

---

### Step 1: Write readiness prompt test

- [ ] Open `frontend/src/pages/WorkoutTrackingPage.test.tsx`

Add test:

```typescript
it('shows readiness prompt at workout start', async () => {
  render(<WorkoutTrackingPage />);
  const startBtn = screen.getByRole('button', { name: /start workout/i });
  fireEvent.click(startBtn);

  expect(screen.getByText(/how are you feeling/i)).toBeInTheDocument();
  const rating = screen.getByRole('button', { name: /4/i }); // 1-5 rating buttons
  fireEvent.click(rating);
  expect(await screen.findByText(/workout started/i)).toBeInTheDocument();
});

it('shows readiness prompt at workout completion', async () => {
  // ... render with active workout ...
  const completeBtn = screen.getByRole('button', { name: /complete workout/i });
  fireEvent.click(completeBtn);

  expect(screen.getByText(/how did you feel/i)).toBeInTheDocument();
  const rating = screen.getByRole('button', { name: /3/i });
  fireEvent.click(rating);
  expect(await screen.findByText(/workout logged/i)).toBeInTheDocument();
});
```

Run: `cd frontend && npm run test -- WorkoutTrackingPage.test.tsx`
Expected: FAIL (readiness UI not implemented).

---

### Step 2: Add ReadinessModal component

- [ ] Create `frontend/src/components/ReadinessModal.tsx`

```typescript
import React, { useState } from 'react';

interface ReadinessModalProps {
  title: string;
  onRate: (readiness: number) => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

export const ReadinessModal: React.FC<ReadinessModalProps> = ({
  title,
  onRate,
  isOpen,
  onClose,
}) => {
  const [selected, setSelected] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleRate = async (readiness: number) => {
    setIsLoading(true);
    try {
      await onRate(readiness);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-sm">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>

        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4, 5].map((num) => (
            <button
              key={num}
              onClick={() => setSelected(num)}
              disabled={isLoading}
              className={`px-4 py-2 rounded border-2 ${
                selected === num
                  ? 'border-blue-600 bg-blue-100'
                  : 'border-gray-300 hover:border-gray-500'
              }`}
            >
              {num}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onClose()}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border rounded"
          >
            Skip
          </button>
          <button
            onClick={() => selected && handleRate(selected)}
            disabled={!selected || isLoading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};
```

---

### Step 3: Integrate ReadinessModal into WorkoutTrackingPage

- [ ] Open `frontend/src/pages/WorkoutTrackingPage.tsx`

Add state and UI:

```typescript
import { ReadinessModal } from '../components/ReadinessModal';
import { useMutation } from '@tanstack/react-query';
import { patchWorkoutReadiness } from '../api/workouts';

// Inside component:
const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);

const readinessMutation = useMutation({
  mutationFn: (readiness: number) =>
    patchWorkoutReadiness(currentWorkout.id, readiness),
  onSuccess: () => {
    if (readinessOpen === 'pre') {
      setReadinessOpen(null);
      // Start workout
    } else if (readinessOpen === 'post') {
      setReadinessOpen(null);
      // Complete workout
    }
  },
});

const handleStartWorkout = () => {
  setReadinessOpen('pre');
};

const handleCompleteWorkout = () => {
  setReadinessOpen('post');
};

// In render:
<ReadinessModal
  title={
    readinessOpen === 'pre'
      ? 'How are you feeling?'
      : 'How did you feel?'
  }
  isOpen={readinessOpen !== null}
  onRate={(readiness) => readinessMutation.mutateAsync(readiness)}
  onClose={() => setReadinessOpen(null)}
/>

<button onClick={handleStartWorkout}>Start Workout</button>
<button onClick={handleCompleteWorkout} disabled={!currentWorkout}>
  Complete Workout
</button>
```

---

### Step 4: Add API function

- [ ] Open `frontend/src/api/workouts.ts` (or create if missing)

```typescript
export const patchWorkoutReadiness = async (
  workoutId: number,
  readiness: number
): Promise<void> => {
  const response = await fetch(
    `/api/v1/users/me/workouts/${workoutId}/readiness`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ readiness }),
    }
  );
  if (!response.ok) throw new Error('Failed to update readiness');
};
```

---

### Step 5: Run tests

- [ ] Run: `cd frontend && npm run test -- WorkoutTrackingPage.test.tsx`
Expected: PASS (readiness prompt tests pass).

- [ ] Run: `cd frontend && npm run type-check`
Expected: PASS.

---

### Step 6: Commit

- [ ] Stage and commit:

```bash
git add frontend/src/components/ReadinessModal.tsx frontend/src/pages/WorkoutTrackingPage.tsx frontend/src/api/workouts.ts
git commit -m "feat(frontend): add readiness prompt at workout start/completion

- ReadinessModal component (1-5 rating, skip option)
- Pre-workout and post-workout prompts
- Integrates PATCH /api/v1/users/me/workouts/{id}/readiness
- Tests: pre/post-workout flow

Claude-Session: https://claude.ai/code/session_01R61M9QX1crhxixZH3f3bpu"
```

---

## Task 4.2: Autoregulation Controller

**Files:**
- Create: `backend/app/services/progression/autoregulation.py`
- Modify: `backend/app/services/program/preview.py` (integrate)
- Create: `backend/tests/services/progression/test_autoregulation.py`

**Interfaces:**
- Consumes: `WorkoutSetLog` query (actual_rpe), `Workout` (target_rpe from `effort_target`), user ID
- Produces: `compute_adjustment(session_logs, exercise_id, model_key) -> (factor: float, reason: str)`

**Context:**
- EWMA: exponentially-weighted moving average, span=3 sessions.
- Signal: `actual_rpe − target_rpe`, smoothed via EWMA.
- Adjustment factor: `clamp(1.0 − k·signal, 0.925, 1.05)` where k=0.075.
- Applied in `preview.py` before `ramp_guard()` call.

---

[Remaining tasks 4.2–4.6 follow same structure but are deferred until tasks 4.1a–d complete. When ready to continue, follow the same bite-sized step pattern for each.]

---

## Execution Strategy

**Parallel tracks (after 4.1a completes):**
1. **Frontend track** (4.1b–d): 2–3 days, minimal backend dependency
2. **Autoregulation track** (4.2–3): 3–4 days, requires 4.1 logging data flowing
3. **Learning/Version tracks** (4.4–5): 2–3 days, independent
4. **Calibration** (4.6): 1–2 days, depends on 4.5 pinning

**Recommended order:** 4.1a (in-flight) → 4.1b–d (frontend, parallel) + 4.4–5 (backend, parallel) → 4.2–3 (depends on 4.1) → 4.6 (depends on 4.5).

---

## Exit Criteria

- ✅ All 6 tasks implemented, committed, pushed to `engine-refactor-phase4`
- ✅ `pytest backend/` ≥80% coverage
- ✅ `mypy app/`, `ruff check .`, `black --check .` all clean
- ✅ Frontend: `npm run test`, `lint`, `type-check`, `build` all clean
- ✅ Alembic migrations (4.5) up/down tested
- ✅ E2E: log RPE > target → autoregulation adjustment; readiness < 3 → deload fires
- ✅ Determinism: same logged inputs → byte-identical load adjustments
