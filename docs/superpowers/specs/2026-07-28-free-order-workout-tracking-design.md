# Free-Order Workout Tracking — Design

**Date:** 2026-07-28
**Status:** Approved

## Problem

`WorkoutTrackingPage` drives the whole workout as a single-file wizard: one exercise is
shown at a time (`useSessionProgress`'s `currentIndex`), the user must log every set of
that exercise in order before the page auto-advances to the next. Feedback from users is
that this doesn't match how they actually train — they want to see the whole workout at
once and log sets in whatever order suits their session (jump ahead to an exercise
they're already set up for, log set 3 before set 2 because that's the one they just did,
come back to something later).

A secondary gap surfaced during design: once a set is logged there's no way to fix it.
`WorkoutSetLog` has a DB `UNIQUE (session_id, workout_exercise_id, set_number)`
constraint, so a second `POST .../set-logs` for the same set fails outright. Supporting
free-order logging without supporting corrections would just relocate the frustration
(fat-fingered a weight, now stuck with it), so this design includes both.

## Approach

**Tracking model:** drop the "current exercise" pointer entirely. `useSessionProgress`
returns per-exercise completion state for *all* exercises at once; the page renders every
exercise as a collapsible section and lets the user open/close/log any of them in any
order. Section open/closed state is UI-only (`useState` in the page), seeded once to
"first incomplete exercise open, rest collapsed" and freely toggled afterward — it is not
persisted, so a reload re-seeds to that same starting point.

Rejected: keeping the wizard for navigation but adding a "jump to exercise" picker on top.
This preserves the auto-advance/current-exercise machinery that the user explicitly
doesn't want, and still forces sequential set logging within an exercise.

**Corrections:** keep `WorkoutSetLog` insert-only (matches its own docstring — "Immutable
per-set performance log" — and the append-only audit-trail pattern `CLAUDE.md` already
establishes for workout logs generally). Drop the unique constraint so a second insert
for the same set succeeds; on every read, dedupe to the highest `id` per
`(workout_exercise_id, set_number)` as the authoritative value. Older rows stay in the
table for audit purposes but are never surfaced.

Rejected: `UPDATE`-in-place for corrections. Requires the same "find the existing row for
this set" lookup as an insert-triggered dedupe, so it isn't actually less code, and it
silently breaks the immutability invariant for this one table while every other log table
in the system stays append-only. Not worth the inconsistency to save a `GROUP BY`.

## Backend Changes

`backend/app/models/logging.py` — remove the `UniqueConstraint` on `WorkoutSetLog`.
Alembic migration drops the corresponding DB constraint (up) and re-adds it (down; down
migration only works if no corrections exist yet, which is fine — it only needs to run
against a pre-feature DB).

`backend/app/crud/logging.py`:
- `append_set_log` unchanged — still a plain insert.
- `get_set_logs` / `get_set_logs_for_sessions` — after fetching, dedupe: group by
  `(workout_exercise_id, set_number)`, keep the row with the max `id` in each group,
  preserve existing ordering behavior for the deduped result.

`backend/app/api/v1/endpoints/sessions.py` — no route changes. `POST
.../sessions/{id}/set-logs` already just calls `append_set_log`; it now succeeds for a
repeat `set_number` instead of raising an integrity error.

## Frontend Data Layer

`useSessionProgress(slots, loggedSets)` reworked:
- Dedupes `loggedSets` client-side the same way the backend does (latest `id` wins per
  `workout_exercise_id` + `set_number`) — defensive, in case a stale cache ever returns
  both rows.
- Returns `exercises: ExerciseProgress[]`, each carrying its `completedSets` keyed by set
  number (not just an append-ordered array — a given set number can now be looked up and
  overwritten by a correction).
- Returns workout-wide aggregates: `totalSets`, `completedSetsTotal`,
  `completedExercises`, `progressPercentage`.
- Removes `currentIndex`, `currentExercise`, `isExerciseComplete`, `isLastExercise`,
  `goToNext` — there is no current exercise anymore.
- `recordSet` becomes `recordSet(workoutExerciseId, setNumber, data)` — used for both a
  first-time log and a correction; the API call shape (`logSessionSet`) is unchanged,
  since the backend already distinguishes "new set" vs. "correction" by whether a row
  exists for that set number.

## UI Components

- `ExerciseSection` (new) — one per slot. Collapsed header shows exercise name, `x/y
  sets`, and a checkmark once complete; expanded body shows target/rest/note info (moved
  out of the old always-visible "Exercise Info" card, since with multiple sections open at
  once that info has to live per-section) plus one `SetRow` per set.
- `SetRow` (new, replaces `SetLogger` + `CompletedSets`) — two states per set:
  - **Unlogged:** compact weight/reps/effort inputs + "Log Set N" button (reuses
    `SetLogger`'s form/validation logic, parameterized by set number instead of always
    "the next one").
  - **Logged:** single-line summary (weight, reps, effort) with a checkmark; tapping it
    swaps back to the input state, pre-filled with the logged values, for correction.
- `CompletedSets` component is removed — its job is now the logged-state `SetRow`.
- Top progress bar keeps its current look (workout-wide `%`, `x/y sets`, `x/y exercises`)
  but no longer reflects a single current exercise.
- Expand All / Collapse All controls above the section list.
- Bottom bar: "Complete Workout" is always enabled. If any set is unlogged, tapping it
  shows a confirmation ("N sets not logged — finish anyway?") before calling
  `completeSession`; if everything's logged it completes immediately. Pre/post readiness
  modal flow is unchanged.

## Testing

Backend: migration up/down test; dedupe unit test (two logs for one set → latest wins,
older row still in DB); integration test that a second `POST .../set-logs` for an
already-logged set succeeds and the session detail reflects the corrected value.

Frontend: `useSessionProgress` tests updated for the new shape (no `currentIndex`, dedupe
behavior, aggregates); `SetRow` unit tests for both states and the edit-tap transition;
`WorkoutTrackingPage` integration tests for out-of-order logging across exercises,
expand/collapse behavior, correcting a logged set, and the always-available Complete
Workout confirmation path.

## Phasing

Two phases, mirroring how the recent sessions work was split:

1. **Backend** — drop constraint, migration, dedupe-on-read, tests. Ships independently;
   existing frontend keeps working unchanged against it (it never posts a duplicate
   set-number today).
2. **Frontend** — `useSessionProgress` rework, `ExerciseSection`/`SetRow`, page rewrite,
   tests. Builds on phase 1 being live.
