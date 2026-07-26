# Design: Wire Live Autoregulation/Deload Signals Into Program Previews

**Date:** 2026-07-26
**Status:** Approved, ready for planning

## Problem

The [load-adjustment reason banner design](./2026-07-26-adjustment-reason-banner-design.md) shipped the *display* side of autoregulation/reactive-deload: `derive_week` already computes `adjustment_reason`, `reactive_deload`, and `deload_reason`, and the frontend already renders them. But `derive_week`'s only caller, `_preview_out` (`backend/app/api/v1/endpoints/programs.py:88-99`), never passes `set_logs_by_exercise` or `readiness_logs` — every preview request gets `autoreg_factor = 1.0` and `reactive_deload_triggered = False` unconditionally. The banner and reason text are fully-built plumbing with nothing flowing through them; no user has ever seen either in practice.

Naively wiring the two log queries into every week of `_preview_out`'s loop (`for w in range(1, program.duration_weeks + 1)`) would be wrong: `derive_week` applies whatever signals it's given to that entire week's schedule, so today's logged RPE/readiness would also silently reshape week 8's preview, weeks that haven't happened yet, and previews of programs the user hasn't started or has already finished.

## Scope

Live signals apply to exactly one week of one program per preview request: the program's *current* week, and only while that program is `ACTIVE`. All other weeks, and all non-`ACTIVE` programs, render exactly as they do today (nominal, `autoreg_factor == 1.0`, no reactive deload).

Two prerequisite gaps surfaced during design and are fixed as part of this work, since "current week" cannot be computed without them:

1. `WorkoutProgram.start_date` is a real column, but nothing ever writes to it. The obvious-looking fix — `ProgramCreationRequest.start_date` — turns out to be dead code: that schema is defined and exported (`schemas/program.py:50`, `schemas/__init__.py:20`) but no endpoint or frontend form uses it. The request type actually wired to program creation is `DraftRequest` (`schemas/program_api.py:71`, extends `MatchRequest`), which has no `start_date` field at all, and `build_draft`'s `WorkoutProgram(...)` construction (`drafting.py:102`) doesn't set one. So this isn't a one-line wiring fix — it's adding a real, user-facing "when do you want to start" field to the draft-creation request and form (confirmed with user: worth doing properly rather than defaulting silently to `today()` at accept time).
2. Existing programs in the database (any status) already have `start_date = NULL` from before this fix, and would otherwise never qualify for live signals even after being accepted.

## Backend Changes

### `backend/app/schemas/program_api.py`
`DraftRequest` (line 71) gains `start_date: date` — a required field, since the frontend form will always send one.

### `backend/app/services/program/drafting.py`
`build_draft` (line 68) gains a new required keyword-only param `start_date: date`, passed straight into the `WorkoutProgram(...)` construction (line 102) as `start_date=start_date`.

### `backend/app/api/v1/endpoints/programs.py` — `draft()`
The `build_draft(...)` call (~line 210) gains `start_date=data.start_date`.

### New migration: backfill `start_date`
```sql
UPDATE workout_programs SET start_date = date(created_at) WHERE start_date IS NULL;
```
Guarded by `IS NULL`, safe to re-run. Applies to all statuses — harmless for `DRAFT`/`ARCHIVED` since neither reaches the live-signal branch below.

### `backend/app/crud/logging.py`
New function, scoped to a specific program's workouts (not the user's full cross-program history) and date-bounded to the deload lookback window:
```python
async def get_workout_logs_for_workouts(
    db: AsyncSession, workout_ids: list[int], user_id: int, since: date
) -> list[UserWorkoutLog]:
    """Readiness logs for a specific program's workouts, for the reactive-deload window."""
```
Set logs need no new crud function — `get_set_logs(db, workout_id, user_id)` (already exists, `logging.py:70`) is called once per `program.workouts` entry and the results grouped into `set_logs_by_exercise: dict[int, list[WorkoutSetLog]]` keyed by `workout_exercise_id`.

### `backend/app/api/v1/endpoints/programs.py` — `_preview_out`
```python
current_week: int | None = None
if program.status == ProgramStatus.ACTIVE and program.start_date is not None:
    w = (date.today() - program.start_date).days // 7 + 1
    current_week = w if 1 <= w <= program.duration_weeks else None

set_logs_by_exercise = None
readiness_logs = None
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
            program, definition, w, exercises,
            set_logs_by_exercise=set_logs_by_exercise if w == current_week else None,
            readiness_logs=readiness_logs if w == current_week else None,
        )
    ]
    for w in range(1, program.duration_weeks + 1)
}
```
Both queries are skipped entirely (no DB round-trip) whenever `current_week is None` — covers `DRAFT`, `ARCHIVED`, not-yet-started (`start_date` in the future), and overrun (`start_date` older than `duration_weeks * 7` days) programs for free.

`_preview_out` needs `user.id` — it's not currently a parameter; every call site already has `user` in scope, so it's added as a required argument.

## Frontend Changes

The "Preferences" step of the program-creation wizard (`ProgramWizardStep1.tsx`, rendered by `ProgramWizard.tsx`, used from `ProgramBuilderPage.tsx` — *not* the unused, unreferenced `ProgramCreationForm.tsx`, which duplicates it but is dead code and is left alone) gains a start-date field:

- `frontend/src/types/programCreation.ts`: `MatchRequest` (the wizard's form-values type, line 82) gains `start_date: string`.
- `frontend/src/types/program.ts`: `DraftRequest` (line 94, the API-facing type) gains `start_date: string`.
- `ProgramWizardStep1.tsx`: new `<FormField type="date" name="start_date" min={today} required />` alongside the existing days-per-week/session-duration fields, defaulting to today's date (`new Date().toISOString().slice(0, 10)`). `min={today}` is a client-side UX guard against picking a past date (which would make `current_week` jump ahead of week 1 immediately on accept) — not enforced server-side, consistent with how the rest of this form's fields are trusted once submitted.
- `ProgramBuilderPage.tsx`: `onPrefs` stores `start_date` on `formPrefs` (already flows through as `FormMatchRequest`); `makeDraft`'s `createDraft.mutateAsync({...})` call (~line 81) adds `start_date: formPrefs.start_date`.

## Edge Cases

- **`start_date` in the future** (accepted but not yet begun): `w < 1` → `current_week = None`. Correct — no logs exist yet regardless.
- **`start_date` older than `duration_weeks * 7` days** (overrun): `w > duration_weeks` → `current_week = None`. No week left to attach signals to.
- **`start_date is None`** (defensive only, post-backfill this shouldn't occur): same as today — no live signals, no crash.
- **Multiple programs, one user**: readiness/set-log queries are scoped by this program's `workout_ids`, so a user's other (past or concurrent) programs never leak signal into this one.
- **Legacy `DRAFT` programs backfilled with a stale `start_date`**: a pre-existing draft created weeks ago, backfilled to `start_date = created_at`, then accepted today, could land mid-program (or past `duration_weeks`) on its very first day as `ACTIVE`. Acceptable one-time quirk for a pre-launch/low-volume dataset — new drafts created after this ships always get a real, user-chosen `start_date` at creation time.

## Non-Goals

- No change to `derive_week`, `compute_adjustment`, or `compute_deload_trigger` — all three already have the right shape and behavior; this work only supplies real arguments.
- No "next week" early-warning preview — deferred; revisit only if users ask for advance notice of an upcoming deload.
- No retroactive display of what autoregulation *would have* shown for already-completed past weeks.

## Testing Plan

**Backend:**
- New test module (e.g. `backend/tests/test_programs_live_signals.py`) covering `_preview_out`:
  - Current week gets live signals when logs warrant it; adjacent weeks (current − 1, current + 1) stay nominal even when the same logs exist.
  - `DRAFT` and `ARCHIVED` programs never get live signals regardless of `start_date` math.
  - `current_week` boundary math: exact week-1 boundary, `start_date` in the future, `start_date` past `duration_weeks * 7` days.
  - `start_date is None` falls back to nominal, no exception.
- `backend/tests/test_logging.py`: `get_workout_logs_for_workouts` excludes other programs' workout IDs and respects `since`.
- `backend/tests/test_programs_flow.py` (or new module): `draft()` requires `start_date`, threads it into the created `WorkoutProgram`.
- Migration test/check: backfill only touches `NULL` rows, idempotent on re-run.

**Frontend:**
- `ProgramWizardStep1` test: date field defaults to today, submits `start_date` as part of the form values.
- `ProgramBuilderPage` test (or its existing flow test): `start_date` from the preferences step reaches the `createDraft` payload.

**Manual:** none beyond confirming the new date field renders and submits correctly in the wizard — the banner/reason rendering itself was already manually verified in the prior plan.
