# Load-Adjustment Reason Banner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface *why* today's loads changed — a dismissible banner when a reactive deload fires, and a friendly per-exercise explanation when autoregulation adjusts a slot's load — closing the Phase 4 sensor-layer UI gap in `docs/technical/PROGRAM_ENGINE_REFACTOR_PLAN.md` (line 184).

**Architecture:** The backend already computes *why* (`autoregulation.compute_adjustment` / `deload.compute_deload_trigger` both return a machine-oriented `reason` string) but `preview.py` discards both. Add two small pure functions that turn the existing signals into one-line, user-facing copy; thread the results through `derive_week`'s output dicts, the Pydantic response schema, and the frontend types, all the way to `WorkoutTrackingPage.tsx`, which renders them via the existing `Alert` component (banner) and the existing `slotNote` label pattern (per-exercise).

**Tech Stack:** FastAPI, Pydantic V2, pytest, React 19 + TypeScript, Vitest + React Testing Library.

## Global Constraints

- **TDD:** Write the failing test before the implementation, for every task.
- **No new endpoint:** both signals ride the existing `GET /programs/{id}/preview` (`derive_week`) response, already consumed by both the multi-week review page and `WorkoutTrackingPage`.
- **Don't change existing function signatures:** `compute_adjustment` and `compute_deload_trigger` keep their current signatures and technical `reason` strings (used for internal traceability) — add new functions alongside them, don't modify them.
- **Type hints:** strict mypy on backend, TypeScript on frontend.
- **Commits:** one commit per task, `Claude-Session` trailer included.

Full spec: `docs/superpowers/specs/2026-07-26-adjustment-reason-banner-design.md`.

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `backend/app/services/progression/autoregulation.py` | Add `describe_adjustment(factor) -> str \| None` |
| `backend/app/services/progression/deload.py` | Add `describe_reactive_deload() -> str` |
| `backend/app/services/progression/__init__.py` | Export the two new functions |
| `backend/tests/services/progression/test_autoregulation.py` | Tests for `describe_adjustment` |
| `backend/tests/services/progression/test_deload.py` | Tests for `describe_reactive_deload` |
| `backend/app/services/program/preview.py` | Wire the two new functions into `derive_week`'s output dicts |
| `backend/app/schemas/program_api.py` | Add `adjustment_reason` to `SlotPreviewOut`, `reactive_deload`/`deload_reason` to `WorkoutPreviewOut` |
| `backend/tests/test_preview.py` | Tests asserting the new fields appear/don't appear on `derive_week`'s output |
| `frontend/src/types/program.ts` | Mirror the three new fields on `SlotPreview`/`WorkoutPreview` |
| `frontend/src/hooks/useWorkoutDetails.ts` | Thread `reactive_deload`/`deload_reason` through `WorkoutDetails` |
| `frontend/src/utils/slotNote.ts` | Add friendly labels for `autoregulated`/`reactive_deload` tags |
| `frontend/src/tests/utils/slotNote.test.ts` | Tests for the two new labels |
| `frontend/src/pages/WorkoutTrackingPage.tsx` | Render the banner (Alert) and the per-exercise reason text |
| `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx` | New test file — banner render/dismiss, per-exercise note+reason |

---

## Task 1: Backend — `describe_adjustment`

**Files:**
- Modify: `backend/app/services/progression/autoregulation.py`
- Modify: `backend/app/services/progression/__init__.py`
- Modify: `backend/tests/services/progression/test_autoregulation.py`

**Interfaces:**
- Consumes: nothing new (pure function of a `float`).
- Produces: `describe_adjustment(factor: float) -> str | None`, importable as `app.services.progression.autoregulation.describe_adjustment` and `app.services.progression.describe_adjustment`. Used by Task 3.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/services/progression/test_autoregulation.py`:

```python
from app.services.progression.autoregulation import (
    ADJUSTMENT_K,
    INSUFFICIENT_HISTORY_REASON,
    MAX_FACTOR,
    MIN_FACTOR,
    compute_adjustment,
    describe_adjustment,
)


def test_describe_adjustment_returns_none_for_neutral_factor():
    assert describe_adjustment(1.0) is None


def test_describe_adjustment_describes_a_load_reduction():
    assert describe_adjustment(0.95) == "Recent sessions ran harder than planned — load reduced 5%"


def test_describe_adjustment_describes_a_load_increase():
    assert describe_adjustment(1.03) == "Recent sessions had room to spare — load increased 3%"


def test_describe_adjustment_at_min_factor_boundary():
    # Floating-point note: (1.0 - 0.925) * 100 == 7.499999999999996 in binary float,
    # not exactly 7.5, so this rounds down to 7 (not a round-half-to-even case).
    assert describe_adjustment(MIN_FACTOR) == "Recent sessions ran harder than planned — load reduced 7%"


def test_describe_adjustment_at_max_factor_boundary():
    assert describe_adjustment(MAX_FACTOR) == "Recent sessions had room to spare — load increased 5%"
```

(Only add the `describe_adjustment` import to the existing `from app.services.progression.autoregulation import (...)` block at the top of the file — don't duplicate the import line.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec backend pytest backend/tests/services/progression/test_autoregulation.py -v`
Expected: FAIL — `ImportError: cannot import name 'describe_adjustment'`

- [ ] **Step 3: Implement `describe_adjustment`**

Append to `backend/app/services/progression/autoregulation.py` (after `compute_adjustment`):

```python
def describe_adjustment(factor: float) -> str | None:
    """One-line, user-facing explanation of an autoregulation adjustment (Task 4.7
    follow-up: PROGRAM_ENGINE_REFACTOR_PLAN.md line 184). `None` when `factor == 1.0`
    (no adjustment was made - insufficient history or a neutral signal); the caller
    should treat `None` as "nothing to show", not as an error."""
    if factor == 1.0:
        return None
    if factor < 1.0:
        pct = round((1.0 - factor) * 100)
        return f"Recent sessions ran harder than planned — load reduced {pct}%"
    pct = round((factor - 1.0) * 100)
    return f"Recent sessions had room to spare — load increased {pct}%"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker-compose exec backend pytest backend/tests/services/progression/test_autoregulation.py -v`
Expected: PASS (all tests, including the 5 new ones)

- [ ] **Step 5: Export from the package `__init__.py`**

In `backend/app/services/progression/__init__.py`, replace the full contents with:

```python
from app.services.progression.autoregulation import compute_adjustment, describe_adjustment  # noqa: F401
from app.services.progression.deload import compute_deload_trigger  # noqa: F401

__all__ = ["compute_adjustment", "describe_adjustment", "compute_deload_trigger"]
```

- [ ] **Step 6: Run mypy**

Run: `docker-compose exec backend mypy app/`
Expected: PASS (no type errors)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/progression/autoregulation.py backend/app/services/progression/__init__.py backend/tests/services/progression/test_autoregulation.py
git commit -m "feat(backend): add describe_adjustment for autoregulation reason copy

Turns the existing autoregulation factor into a one-line, user-facing
explanation (Phase 4 sensor-layer UI gap). compute_adjustment's
signature and technical reason string are unchanged.

Claude-Session: https://claude.ai/code/session_01KodZ1LEDUDxdMCQQLmdVq9"
```

---

## Task 2: Backend — `describe_reactive_deload`

**Files:**
- Modify: `backend/app/services/progression/deload.py`
- Modify: `backend/app/services/progression/__init__.py`
- Modify: `backend/tests/services/progression/test_deload.py`

**Interfaces:**
- Consumes: nothing (no parameters).
- Produces: `describe_reactive_deload() -> str`, importable as `app.services.progression.deload.describe_reactive_deload` and `app.services.progression.describe_reactive_deload`. Used by Task 3.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services/progression/test_deload.py`:

```python
from app.services.progression.deload import (
    INSUFFICIENT_SIGNAL_REASON,
    compute_deload_trigger,
    describe_reactive_deload,
)


def test_describe_reactive_deload_returns_fixed_user_facing_copy():
    assert describe_reactive_deload() == "Readiness has been low recently — built in a lighter week"
```

(Only add the `describe_reactive_deload` import to the existing `from app.services.progression.deload import (...)` block at the top of the file — don't duplicate the import line.)

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest backend/tests/services/progression/test_deload.py -v`
Expected: FAIL — `ImportError: cannot import name 'describe_reactive_deload'`

- [ ] **Step 3: Implement `describe_reactive_deload`**

Append to `backend/app/services/progression/deload.py` (after `compute_deload_trigger`):

```python
def describe_reactive_deload() -> str:
    """One-line, user-facing explanation shown when a reactive deload fires (Task 4.7
    follow-up: PROGRAM_ENGINE_REFACTOR_PLAN.md line 184). Static copy is intentional:
    the *why* (low readiness) is always the same story; the specific dates/counts
    already live in compute_deload_trigger's technical reason string, used for
    internal traceability rather than shown to the user."""
    return "Readiness has been low recently — built in a lighter week"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest backend/tests/services/progression/test_deload.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Update the package `__init__.py`**

In `backend/app/services/progression/__init__.py`, replace the full contents with:

```python
from app.services.progression.autoregulation import compute_adjustment, describe_adjustment  # noqa: F401
from app.services.progression.deload import compute_deload_trigger, describe_reactive_deload  # noqa: F401

__all__ = [
    "compute_adjustment",
    "describe_adjustment",
    "compute_deload_trigger",
    "describe_reactive_deload",
]
```

- [ ] **Step 6: Run mypy**

Run: `docker-compose exec backend mypy app/`
Expected: PASS (no type errors)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/progression/deload.py backend/app/services/progression/__init__.py backend/tests/services/progression/test_deload.py
git commit -m "feat(backend): add describe_reactive_deload for deload reason copy

Turns the existing readiness-based deload trigger into a one-line,
user-facing explanation (Phase 4 sensor-layer UI gap).
compute_deload_trigger's signature and technical reason string are
unchanged.

Claude-Session: https://claude.ai/code/session_01KodZ1LEDUDxdMCQQLmdVq9"
```

---

## Task 3: Backend — Wire into `derive_week` and the response schema

**Files:**
- Modify: `backend/app/services/program/preview.py:12-13` (imports), `:118-122` (deload trigger block), `:140-146` (autoregulation block), `:165-183` (slot/day dict construction)
- Modify: `backend/app/schemas/program_api.py:85-107` (`SlotPreviewOut`, `WorkoutPreviewOut`)
- Modify: `backend/tests/test_preview.py`

**Interfaces:**
- Consumes: `describe_adjustment` (Task 1), `describe_reactive_deload` (Task 2).
- Produces: `derive_week`'s per-slot dicts now include `"adjustment_reason": str | None`; per-workout-day dicts now include `"reactive_deload": bool` and `"deload_reason": str | None`. `SlotPreviewOut.adjustment_reason: str | None`, `WorkoutPreviewOut.reactive_deload: bool`, `WorkoutPreviewOut.deload_reason: str | None`. Consumed by Task 4 (frontend types).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_preview.py` (after `test_derive_week_reactive_deload_determinism_same_history_byte_identical`, i.e. at the end of the file):

```python
@pytest.mark.asyncio
async def test_derive_week_includes_adjustment_reason_when_autoregulated(sample_template_orm, sample_exercises):
    """A slot whose load was cut by autoregulation carries a plain-language
    adjustment_reason alongside the existing 'autoregulated' note tag."""
    definition, program, exercise_map = _intermediate_program(sample_template_orm, sample_exercises)
    target_we = next(ex for w in program.workouts for ex in w.exercises if ex.target_rpe is not None)
    overshoot_rpe = target_we.target_rpe + 2.0
    logs = {target_we.id: [_set_log(target_we.id, 1, overshoot_rpe), _set_log(target_we.id, 2, overshoot_rpe)]}

    adjusted = derive_week(program, definition, 1, exercise_map, logs)
    slot = next(s for d in adjusted for s in d["slots"] if s["workout_exercise_id"] == target_we.id)

    # This overshoot clamps the factor to MIN_FACTOR (0.925); see the
    # test_autoregulation.py boundary test for why that's 7%, not 7.5% rounded up.
    assert slot["adjustment_reason"] == "Recent sessions ran harder than planned — load reduced 7%"


@pytest.mark.asyncio
async def test_derive_week_adjustment_reason_is_none_without_autoregulation(sample_template_orm, sample_exercises):
    """Slots that weren't autoregulated (insufficient history, or no logs passed)
    carry adjustment_reason=None."""
    definition, program, exercise_map = _intermediate_program(sample_template_orm, sample_exercises)

    baseline = derive_week(program, definition, 1, exercise_map)
    assert all(s["adjustment_reason"] is None for d in baseline for s in d["slots"])


@pytest.mark.asyncio
async def test_derive_week_includes_reactive_deload_flag_and_reason_when_triggered(
    sample_template_orm, sample_exercises
):
    """Workout-day dicts carry reactive_deload=True and a plain-language deload_reason
    when the readiness-based trigger fires."""
    definition, program, exercise_map = _intermediate_program(sample_template_orm, sample_exercises)
    logs = [_readiness_log(1, 2), _readiness_log(5, 1)]

    adjusted = derive_week(
        program, definition, 1, exercise_map, readiness_logs=logs, reference_date=_REACTIVE_DELOAD_REFERENCE
    )

    assert all(d["reactive_deload"] is True for d in adjusted)
    assert all(d["deload_reason"] == "Readiness has been low recently — built in a lighter week" for d in adjusted)


@pytest.mark.asyncio
async def test_derive_week_reactive_deload_flag_is_false_without_trigger(sample_template_orm, sample_exercises):
    """Workout-day dicts carry reactive_deload=False and deload_reason=None when the
    readiness trigger hasn't fired (including when no readiness_logs are passed)."""
    definition, program, exercise_map = _intermediate_program(sample_template_orm, sample_exercises)

    baseline = derive_week(program, definition, 1, exercise_map)

    assert all(d["reactive_deload"] is False for d in baseline)
    assert all(d["deload_reason"] is None for d in baseline)


@pytest.mark.asyncio
async def test_derive_week_workout_preview_out_roundtrip_with_new_fields(sample_template_orm, sample_exercises):
    """WorkoutPreviewOut(**day) round-trips the new reactive_deload/deload_reason
    fields, and SlotPreviewOut(**slot) round-trips adjustment_reason."""
    from app.schemas.program_api import WorkoutPreviewOut

    definition, program, exercise_map = _intermediate_program(sample_template_orm, sample_exercises)
    logs = [_readiness_log(1, 2), _readiness_log(5, 1)]

    week1 = derive_week(
        program, definition, 1, exercise_map, readiness_logs=logs, reference_date=_REACTIVE_DELOAD_REFERENCE
    )
    for day in week1:
        out = WorkoutPreviewOut(**day)
        assert out.reactive_deload is True
        assert out.deload_reason == "Readiness has been low recently — built in a lighter week"
        for slot_out in out.slots:
            assert hasattr(slot_out, "adjustment_reason")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec backend pytest backend/tests/test_preview.py -v -k "adjustment_reason or reactive_deload_flag or workout_preview_out_roundtrip_with_new"`
Expected: FAIL — `KeyError: 'adjustment_reason'` (and similar for `reactive_deload`/`deload_reason`)

- [ ] **Step 3: Update imports in `preview.py`**

In `backend/app/services/program/preview.py`, change:

```python
from app.services.progression.autoregulation import compute_adjustment
from app.services.progression.deload import compute_deload_trigger
```

to:

```python
from app.services.progression.autoregulation import compute_adjustment, describe_adjustment
from app.services.progression.deload import compute_deload_trigger, describe_reactive_deload
```

- [ ] **Step 4: Wire the deload reason into `derive_week`**

Change:

```python
    reactive_deload_triggered = False
    if readiness_logs:
        reactive_deload_triggered, _reactive_deload_reason = compute_deload_trigger(
            readiness_logs, reference_date or date.today()
        )
```

to:

```python
    reactive_deload_triggered = False
    deload_reason: str | None = None
    if readiness_logs:
        reactive_deload_triggered, _reactive_deload_reason = compute_deload_trigger(
            readiness_logs, reference_date or date.today()
        )
        if reactive_deload_triggered:
            deload_reason = describe_reactive_deload()
```

- [ ] **Step 5: Wire the adjustment reason into the per-slot loop**

Change:

```python
            autoreg_factor = 1.0
            if ex.target_rpe is not None and set_logs_by_exercise:
                logs_for_slot = set_logs_by_exercise.get(ex.id, [])
                if logs_for_slot:
                    autoreg_factor, _reason = compute_adjustment(
                        logs_for_slot, ex.id, definition.progression.model_key, ex.target_rpe
                    )
```

to:

```python
            autoreg_factor = 1.0
            adjustment_reason: str | None = None
            if ex.target_rpe is not None and set_logs_by_exercise:
                logs_for_slot = set_logs_by_exercise.get(ex.id, [])
                if logs_for_slot:
                    autoreg_factor, _reason = compute_adjustment(
                        logs_for_slot, ex.id, definition.progression.model_key, ex.target_rpe
                    )
                    adjustment_reason = describe_adjustment(autoreg_factor)
```

- [ ] **Step 6: Add the new fields to the slot and day dicts**

Change the slot dict:

```python
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": resolved_exercise_id,
                    "exercise_name": exercise_name,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": rest_seconds,
                    "note": scheme.note,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                    "effort_target": _effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method),
                    "rotation_pool": ex.rotation_pool,
                    "tempo": "controlled",
                    "warmup_sets": warmup_sets,
                }
            )
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
```

to:

```python
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": resolved_exercise_id,
                    "exercise_name": exercise_name,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": rest_seconds,
                    "note": scheme.note,
                    "adjustment_reason": adjustment_reason,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                    "effort_target": _effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method),
                    "rotation_pool": ex.rotation_pool,
                    "tempo": "controlled",
                    "warmup_sets": warmup_sets,
                }
            )
        days.append(
            {
                "workout_id": workout.id,
                "key": workout.key,
                "name": workout.name,
                "slots": slots,
                "reactive_deload": reactive_deload_triggered,
                "deload_reason": deload_reason,
            }
        )
```

- [ ] **Step 7: Update `SlotPreviewOut` and `WorkoutPreviewOut`**

In `backend/app/schemas/program_api.py`, change:

```python
class SlotPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    is_locked: bool
    is_user_swapped: bool
    effort_target: dict[str, object] | None = None
    rotation_pool: list[int] = []
    tempo: str
    warmup_sets: list[WarmupSetOut] = []


class WorkoutPreviewOut(BaseModel):
    workout_id: int
    key: str
    name: str
    slots: list[SlotPreviewOut]
```

to:

```python
class SlotPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    adjustment_reason: str | None = None
    is_locked: bool
    is_user_swapped: bool
    effort_target: dict[str, object] | None = None
    rotation_pool: list[int] = []
    tempo: str
    warmup_sets: list[WarmupSetOut] = []


class WorkoutPreviewOut(BaseModel):
    workout_id: int
    key: str
    name: str
    slots: list[SlotPreviewOut]
    reactive_deload: bool = False
    deload_reason: str | None = None
```

- [ ] **Step 8: Run the new and existing preview tests**

Run: `docker-compose exec backend pytest backend/tests/test_preview.py -v`
Expected: PASS (all tests, including the 5 new ones — this also re-runs every pre-existing `derive_week` test to confirm nothing else broke)

- [ ] **Step 9: Run the full backend suite, mypy, ruff**

Run: `docker-compose exec backend pytest`
Expected: PASS (≥80% coverage maintained)

Run: `docker-compose exec backend mypy app/`
Expected: PASS

Run: `docker-compose exec backend ruff check .`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/program/preview.py backend/app/schemas/program_api.py backend/tests/test_preview.py
git commit -m "feat(backend): surface adjustment/deload reasons in program preview response

Wires the previously-discarded reason strings (_reason,
_reactive_deload_reason) through derive_week as adjustment_reason
(per-slot) and reactive_deload/deload_reason (per-workout-day), and
adds the matching fields to SlotPreviewOut/WorkoutPreviewOut. No new
endpoint - both signals ride the existing GET /programs/{id}/preview
response already consumed by WorkoutTrackingPage.

Claude-Session: https://claude.ai/code/session_01KodZ1LEDUDxdMCQQLmdVq9"
```

---

## Task 4: Frontend — Types, hook, and note labels

**Files:**
- Modify: `frontend/src/types/program.ts`
- Modify: `frontend/src/hooks/useWorkoutDetails.ts`
- Modify: `frontend/src/utils/slotNote.ts`
- Modify: `frontend/src/tests/utils/slotNote.test.ts`

**Interfaces:**
- Consumes: the three new backend fields from Task 3 (`adjustment_reason`, `reactive_deload`, `deload_reason`).
- Produces: `SlotPreview.adjustment_reason: string | null`, `WorkoutPreview.reactive_deload: boolean`, `WorkoutPreview.deload_reason: string | null`, `WorkoutDetails.reactive_deload: boolean`, `WorkoutDetails.deload_reason: string | null`, and `formatSlotNote('autoregulated')`/`formatSlotNote('reactive_deload')` friendly labels. Consumed by Task 5.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/tests/utils/slotNote.test.ts`:

```typescript
it('labels an autoregulated note', () => {
  expect(formatSlotNote('autoregulated')).toBe('Load adjusted');
});

it('labels a reactive_deload note the same as a scheduled deload', () => {
  expect(formatSlotNote('reactive_deload')).toBe('Deload week');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test -- slotNote.test.ts`
Expected: FAIL — both new labels currently fall through to the "renders as-is" default (`'autoregulated'` and `'reactive_deload'` returned verbatim, not the friendly labels)

- [ ] **Step 3: Update `slotNote.ts`**

Change:

```typescript
const NOTE_LABELS: Record<string, string> = {
  deload: 'Deload week',
  ramp_capped: 'Capped for safe progression',
};
```

to:

```typescript
const NOTE_LABELS: Record<string, string> = {
  deload: 'Deload week',
  ramp_capped: 'Capped for safe progression',
  autoregulated: 'Load adjusted',
  reactive_deload: 'Deload week',
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test -- slotNote.test.ts`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Update `SlotPreview`/`WorkoutPreview` types**

In `frontend/src/types/program.ts`, change:

```typescript
export interface SlotPreview {
  workout_exercise_id: number;
  exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  is_locked: boolean;
  is_user_swapped: boolean;
  effort_target: EffortTarget | null;
  rotation_pool: number[];
  tempo: string;
  warmup_sets: WarmupSet[];
}

export interface WorkoutPreview {
  workout_id: number;
  key: string;
  name: string;
  slots: SlotPreview[];
}
```

to:

```typescript
export interface SlotPreview {
  workout_exercise_id: number;
  exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  adjustment_reason: string | null;
  is_locked: boolean;
  is_user_swapped: boolean;
  effort_target: EffortTarget | null;
  rotation_pool: number[];
  tempo: string;
  warmup_sets: WarmupSet[];
}

export interface WorkoutPreview {
  workout_id: number;
  key: string;
  name: string;
  slots: SlotPreview[];
  reactive_deload: boolean;
  deload_reason: string | null;
}
```

- [ ] **Step 6: Thread the workout-level fields through `useWorkoutDetails`**

In `frontend/src/hooks/useWorkoutDetails.ts`, change:

```typescript
export interface WorkoutDetails {
  workout_id: number;
  name: string;
  slots: SlotPreview[];
  program_id: number;
}
```

to:

```typescript
export interface WorkoutDetails {
  workout_id: number;
  name: string;
  slots: SlotPreview[];
  program_id: number;
  reactive_deload: boolean;
  deload_reason: string | null;
}
```

And change:

```typescript
        if (workout) {
          return {
            workout_id: workoutId,
            name: workout.name,
            slots: workout.slots,
            program_id: programId || 0,
          };
        }
```

to:

```typescript
        if (workout) {
          return {
            workout_id: workoutId,
            name: workout.name,
            slots: workout.slots,
            program_id: programId || 0,
            reactive_deload: workout.reactive_deload,
            deload_reason: workout.deload_reason,
          };
        }
```

- [ ] **Step 7: Run type-check**

Run: `docker-compose exec frontend npm run type-check`
Expected: PASS. If it fails because an unrelated test fixture (e.g. `frontend/src/tests/pages/ProgramPreviewPage.test.tsx`'s mocked `WorkoutPreview` object literals) is now missing `reactive_deload`/`deload_reason`, add `reactive_deload: false, deload_reason: null` to each mocked workout object there — that file's mocks intentionally mirror the full backend shape (see its existing `rotation_pool`/`tempo`/`warmup_sets` fields).

- [ ] **Step 8: Run the full frontend test suite**

Run: `docker-compose exec frontend npm run test`
Expected: PASS (no regressions)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/types/program.ts frontend/src/hooks/useWorkoutDetails.ts frontend/src/utils/slotNote.ts frontend/src/tests/utils/slotNote.test.ts
git commit -m "feat(frontend): thread adjustment/deload reason fields through types

Mirrors the three new backend fields (adjustment_reason,
reactive_deload, deload_reason) on SlotPreview/WorkoutPreview and
WorkoutDetails, and gives the autoregulated/reactive_deload note tags
friendly labels via the existing slotNote pattern.

Claude-Session: https://claude.ai/code/session_01KodZ1LEDUDxdMCQQLmdVq9"
```

---

## Task 5: Frontend — Banner and per-exercise reason on `WorkoutTrackingPage`

**Files:**
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx`
- Create: `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx`

**Interfaces:**
- Consumes: `WorkoutDetails.reactive_deload`/`deload_reason` and `SlotPreview.adjustment_reason` (Task 4), `Alert` component (`frontend/src/components/Alert.tsx`, already exported from `@/components`), `formatSlotNote` (`frontend/src/utils/slotNote.ts`).
- Produces: no new exports — this is the final UI consumer.

`WorkoutTrackingPage.tsx` currently has no test file at all — this task creates the first one, scoped to the new banner/reason behavior (not full page coverage, which is out of scope for this feature).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/tests/pages/WorkoutTrackingPage.test.tsx`:

```typescript
import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';

vi.mock('@/store/auth');
vi.mock('@/hooks/useWorkoutDetails');
vi.mock('@/api/logging', () => ({ logSetLog: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@/api/workouts', () => ({ postWorkoutReadiness: vi.fn().mockResolvedValue(undefined) }));

import { useAuthStore } from '@/store/auth';
import { useWorkoutDetails } from '@/hooks/useWorkoutDetails';

const baseWorkoutDetails = {
  workout_id: 1,
  name: 'Day A',
  program_id: 1,
  reactive_deload: false,
  deload_reason: null,
  slots: [
    {
      workout_exercise_id: 1,
      exercise_id: 10,
      exercise_name: 'Bench Press',
      sets: 3,
      reps: 8,
      load: 100,
      rest_seconds: 120,
      note: null,
      adjustment_reason: null,
      is_locked: false,
      is_user_swapped: false,
      effort_target: null,
      rotation_pool: [],
      tempo: 'controlled',
      warmup_sets: [],
    },
  ],
};

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/workouts/1?programId=1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/workouts/:workoutId" element={<WorkoutTrackingPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(useAuthStore).mockReturnValue({ userProfile: { effort_method: 'rpe' } } as any);
});

it('renders the reactive deload banner when the workout was deloaded', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      reactive_deload: true,
      deload_reason: 'Readiness has been low recently — built in a lighter week',
    },
    isLoading: false,
    error: null,
  } as any);

  renderPage();

  expect(screen.getByText('Readiness has been low recently — built in a lighter week')).toBeInTheDocument();
});

it('does not render the banner when the workout was not deloaded', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: baseWorkoutDetails,
    isLoading: false,
    error: null,
  } as any);

  renderPage();

  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('dismisses the deload banner on click and it stays dismissed', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      reactive_deload: true,
      deload_reason: 'Readiness has been low recently — built in a lighter week',
    },
    isLoading: false,
    error: null,
  } as any);

  renderPage();

  fireEvent.click(screen.getByLabelText('Dismiss alert'));

  expect(screen.queryByText('Readiness has been low recently — built in a lighter week')).not.toBeInTheDocument();
});

it('shows a friendly label and the reason for an autoregulated exercise', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      slots: [
        {
          ...baseWorkoutDetails.slots[0],
          note: 'autoregulated',
          adjustment_reason: 'Recent sessions ran harder than planned — load reduced 5%',
        },
      ],
    },
    isLoading: false,
    error: null,
  } as any);

  renderPage();

  expect(screen.getByText('Load adjusted')).toBeInTheDocument();
  expect(screen.getByText('Recent sessions ran harder than planned — load reduced 5%')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker-compose exec frontend npm run test -- WorkoutTrackingPage.test.tsx`
Expected: FAIL — banner text/`Load adjusted` label not found (current page renders the raw `note` string, no banner)

- [ ] **Step 3: Add the `Alert` import and dismiss state**

In `frontend/src/pages/WorkoutTrackingPage.tsx`, change:

```typescript
import {
  SetLogger,
  CompletedSets,
  Toast,
  Button,
  Card,
  ReadinessModal,
  Spinner,
} from '@/components';
import type { EffortMethod } from '@/types/programCreation';
```

to:

```typescript
import {
  SetLogger,
  CompletedSets,
  Toast,
  Button,
  Card,
  ReadinessModal,
  Spinner,
  Alert,
} from '@/components';
import { formatSlotNote } from '@/utils/slotNote';
import type { EffortMethod } from '@/types/programCreation';
```

- [ ] **Step 4: Add `adjustment_reason` to the `ExerciseProgress` interface**

Change:

```typescript
interface ExerciseProgress {
  workout_exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  completedSets: LoggedSet[];
}
```

to:

```typescript
interface ExerciseProgress {
  workout_exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  adjustment_reason: string | null;
  completedSets: LoggedSet[];
}
```

- [ ] **Step 5: Populate `adjustment_reason` when building `exercises`, and add dismiss state**

Change:

```typescript
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);

  // Initialize exercises from workout details
  useEffect(() => {
    if (workoutDetails?.slots) {
      const exs = workoutDetails.slots.map((slot) => ({
        workout_exercise_id: slot.workout_exercise_id,
        exercise_name: slot.exercise_name,
        sets: slot.sets,
        reps: slot.reps,
        load: slot.load,
        rest_seconds: slot.rest_seconds,
        note: slot.note,
        completedSets: [],
      }));
      setExercises(exs);
      setCurrentExerciseIndex(0);
    }
  }, [workoutDetails]);
```

to:

```typescript
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);
  const [deloadBannerDismissed, setDeloadBannerDismissed] = useState(false);

  // Initialize exercises from workout details
  useEffect(() => {
    if (workoutDetails?.slots) {
      const exs = workoutDetails.slots.map((slot) => ({
        workout_exercise_id: slot.workout_exercise_id,
        exercise_name: slot.exercise_name,
        sets: slot.sets,
        reps: slot.reps,
        load: slot.load,
        rest_seconds: slot.rest_seconds,
        note: slot.note,
        adjustment_reason: slot.adjustment_reason,
        completedSets: [],
      }));
      setExercises(exs);
      setCurrentExerciseIndex(0);
    }
  }, [workoutDetails]);
```

- [ ] **Step 6: Render the banner**

Change:

```typescript
      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 pb-24">
          {/* Set Logger */}
          <Card className="mb-8">
```

to:

```typescript
      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 pb-24">
          {/* Reactive Deload Banner */}
          {workoutDetails.reactive_deload && !deloadBannerDismissed && workoutDetails.deload_reason && (
            <Alert
              type="info"
              dismissible
              onDismiss={() => setDeloadBannerDismissed(true)}
              className="mb-4"
            >
              {workoutDetails.deload_reason}
            </Alert>
          )}

          {/* Set Logger */}
          <Card className="mb-8">
```

- [ ] **Step 7: Render the friendly label and reason for the per-exercise note**

Change:

```typescript
              {currentExercise.note && (
                <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-2">Note</p>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    {currentExercise.note}
                  </p>
                </div>
              )}
```

to:

```typescript
              {currentExercise.note && (
                <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-2">Note</p>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    {formatSlotNote(currentExercise.note)}
                  </p>
                  {currentExercise.adjustment_reason && (
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                      {currentExercise.adjustment_reason}
                    </p>
                  )}
                </div>
              )}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `docker-compose exec frontend npm run test -- WorkoutTrackingPage.test.tsx`
Expected: PASS (all 4 new tests)

- [ ] **Step 9: Run the full frontend suite, type-check, lint**

Run: `docker-compose exec frontend npm run test`
Expected: PASS (no regressions)

Run: `docker-compose exec frontend npm run type-check`
Expected: PASS

Run: `docker-compose exec frontend npm run lint`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/WorkoutTrackingPage.tsx frontend/src/tests/pages/WorkoutTrackingPage.test.tsx
git commit -m "feat(frontend): render adjustment/deload reason banner on WorkoutTrackingPage

Closes the Phase 4 sensor-layer UI gap (PROGRAM_ENGINE_REFACTOR_PLAN.md
line 184): a dismissible Alert banner explains a reactive deload, and
the per-exercise note now shows a friendly label plus the
autoregulation reason instead of a raw engine tag. First test file for
this page - scoped to the new behavior, not full coverage.

Claude-Session: https://claude.ai/code/session_01KodZ1LEDUDxdMCQQLmdVq9"
```

---

## Execution Strategy

Sequential — each task builds on the previous one's exports:
1. Task 1 (autoregulation copy) and Task 2 (deload copy) are independent of each other and could run in parallel, but both must land before Task 3.
2. Task 3 (backend wiring) must complete before Task 4 (frontend types) — Task 4 mirrors Task 3's exact field names.
3. Task 4 must complete before Task 5 (UI) — Task 5 consumes the types Task 4 defines.

## Exit Criteria

- [ ] `describe_adjustment`/`describe_reactive_deload` unit-tested (neutral/reduction/increase/boundary cases)
- [ ] `derive_week` output includes `adjustment_reason` (per-slot) and `reactive_deload`/`deload_reason` (per-workout-day), tested both triggered and not-triggered
- [ ] `SlotPreviewOut`/`WorkoutPreviewOut` round-trip the new fields
- [ ] `pytest backend/` ≥80% coverage maintained; `mypy app/`, `ruff check .` clean
- [ ] Frontend types (`SlotPreview`, `WorkoutPreview`, `WorkoutDetails`) mirror the backend fields exactly
- [ ] `WorkoutTrackingPage` shows a dismissible banner when `reactive_deload` is true, and a friendly label + reason for an autoregulated exercise
- [ ] Frontend: `npm run test`, `lint`, `type-check` all clean
