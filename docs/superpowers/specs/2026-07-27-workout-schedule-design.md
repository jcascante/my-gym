# Workout Schedule — Design

**Date:** 2026-07-27
**Status:** Approved

## Problem

From the dashboard, tapping "Today's workout" drops the user straight into logging the
first exercise. There is no way to see what is scheduled, what was completed, or what is
coming — the things every training app puts between the home screen and the logger.

The gap is not only in the UI. There is no schedule in the data model:

- `Workout` has `key`, `name`, `order` — no date, no status.
- `derive_week` (`backend/app/services/program/preview.py:126`) re-renders the *same*
  `program.workouts` rows for every week. Only the prescribed load and reps differ, so
  `workout_id` does not identify a session — week 1's "Upper Body A" and week 3's share
  an id. `useWorkoutDetails.ts:44-60` already works around this by preferring
  `current_week` and falling back to a scan.
- `WorkoutSetLog.workout_id` therefore cannot say *which week's* session was logged.
  Only `created_at` can, and only by inference.
- The dashboard's "Today" card (`DashboardPage.tsx:32`) is really "first workout of the
  current week". It is not date-aware and does not know whether the session was done.

`Workout` is a template row wearing a session's clothes. Every symptom above follows from
that. This design separates the two.

## Approach

Materialize sessions as real rows: one per (program, week, workout template), carrying a
`scheduled_date` and a `status`. The calendar becomes a date-range query, set logs get an
unambiguous anchor, and rescheduling later becomes a column update.

Rejected: deriving dates and statuses on the fly from `start_date` and log timestamps. It
needs no migration, but it cannot distinguish a session logged a day late from a missed
one, cannot represent an intentional skip, keeps `workout_id` ambiguous, and leaves the
already-requested "edit training days" feature with nothing to edit.

## Data Model

New table `workout_sessions`:

| column           | type                  | notes                    |
| ---------------- | --------------------- | ------------------------ |
| `id`             | int PK                |                          |
| `program_id`     | FK `workout_programs` | indexed                  |
| `workout_id`     | FK `workouts`         | the template row         |
| `week`           | int                   | 1..`duration_weeks`      |
| `scheduled_date` | date                  | indexed                  |
| `status`         | enum                  | see below                |
| `completed_at`   | datetime, nullable    |                          |

`UNIQUE (program_id, workout_id, week)`.

`workout_set_logs` gains a nullable `session_id` FK to `workout_sessions`.

### Status

`scheduled` | `in_progress` | `completed` | `missed` | `skipped`

`in_progress` exists to protect the lazy missed-flip. The first set log moves a session
`scheduled → in_progress`; completing it moves it to `completed`. The flip only ever
touches rows still in `scheduled`, so a session the user started and abandoned stays
`in_progress` instead of being mislabelled `missed`.

`skipped` is in the enum but nothing writes it yet. It is reserved so that adding a
"skip this session" action later does not require a migration.

### Date derivation

```
scheduled_date = program.start_date + (week - 1) * 7 + offset[i]
```

where `i` is the workout's `order` within the week. Offsets are evenly spread weekdays
counted from `start_date`'s own weekday:

```
n = len(program.workouts), clamped to 1..7

1 → [0]              4 → [0, 1, 3, 4]        7 → [0, 1, 2, 3, 4, 5, 6]
2 → [0, 3]           5 → [0, 1, 2, 3, 4]
3 → [0, 2, 4]        6 → [0, 1, 2, 3, 4, 5]
```

The resolved offsets are written to `program.constraints.training_day_offsets` at
activation, so dates stay stable even if the spread table is later changed.

**Out of scope, noted for a later task:** letting the user choose their own training days
from `/schedule`. `training_day_offsets` is where that edit would land.

### Materialization

Sessions are written on the DRAFT → ACTIVE transition — the only point at which both
`start_date` and `duration_weeks` are fixed. `duration_weeks × len(program.workouts)`
rows are inserted with `status = 'scheduled'`.

The Alembic migration is schema-only. Programs already ACTIVE get no sessions and show an
empty schedule until re-activated; existing set logs keep `session_id = NULL`. This is a
deliberate call — no environment has history worth preserving.

## API

All endpoints under `/api/v1/users/me`, ownership-scoped via `program.user_id`.

```
GET  /schedule?start=<date>&end=<date>
     → [{ session_id, scheduled_date, week, status,
           workout_name, exercise_count, duration_min }]

GET  /sessions/{session_id}
     → { session_id, scheduled_date, week, status, workout_name,
         program_id, program_name, slots[], logged_sets[],
         reactive_deload, deload_reason }

POST /sessions/{session_id}/set-logs      → appends a set; scheduled → in_progress
POST /sessions/{session_id}/readiness     → pre/post readiness, unchanged semantics
POST /sessions/{session_id}/complete      → status = completed, completed_at = now()
```

`slots[]` comes from `derive_week(program, definition, session.week)` — the same call
`_preview_out` makes — so prescriptions are week-correct with no `current_week` guessing.
`logged_sets[]` is populated for `in_progress` and `completed` sessions and drives the
read-only past-session view. `exercise_count` is `len(workout.exercises)`;
`duration_min` is the user profile's `workout_duration_min`, matching what the dashboard
card already displays.

Dates are compared server-side against `date.today()`, consistent with the existing
`current_week` derivation (`programs.py:112`). Per-user timezones are not modelled
anywhere in the app today and are not introduced here.

### The lazy missed-flip

One service function, called at the top of both `GET /schedule` and
`GET /sessions/{session_id}`:

```sql
UPDATE workout_sessions SET status = 'missed'
WHERE program_id = ? AND status = 'scheduled' AND scheduled_date < :today
```

Written once, tested once, and no read path can observe a stale `scheduled` row. No
scheduler or worker is introduced.

### Unchanged

`current_week` in `programs.py:110-113` stays as-is — program preview still needs it.

## Session Anchoring (scope extension)

The sections above make sessions the anchor for *scheduling*. This section makes them the
anchor for *logging* too, removing the timestamp inference that currently stands in for
it. Decided after the initial design, on the principle that dev-stage code should be
made correct rather than preserved.

### Both log tables become session-scoped

`WorkoutSetLog.session_id` and `UserWorkoutLog.session_id` are **NOT NULL** FKs. A log
that cannot name its session cannot be written. This is what makes the week-ambiguity
problem structurally impossible rather than merely avoided by convention.

Consequently these are **deleted**, not deprecated:

- `POST/GET /workouts/{id}/sets`, `POST /workouts/{id}/logs`, `GET /workouts/{id}/logs/{log_id}`
- `POST /users/me/workouts/{id}/set-logs`, `POST /users/me/workouts/{id}/readiness`
- `schemas.logging.WorkoutSetLogCreate` (superseded by `SessionSetLogCreate`)
- the duplicate `router` / `users_workout_router` split in `logging.py:19-20`

Session-scoped routes are the only way to log. With `WorkoutSetLogCreate` gone there is no
second validator set to duplicate or share.

### The live-signal queries stop inferring

Two heuristics exist today only because logs could not name their session:

**`compute_adjustment` groups by calendar date.** `_session_key`
(`autoregulation.py:52-54`) buckets set logs by `created_at.date()`. Two sessions on one
day merge into a single EWMA sample; one session spanning midnight splits into two. It
groups by `log.session_id` instead — exact by construction.

**`_preview_out` fans out by `workout_id` + a date window.**
`get_set_logs_for_workouts` and `get_workout_logs_for_workouts` (`programs.py:115-123`)
take every workout id in the program and filter on `created_at >= today - 14d`. They are
replaced by session-scoped queries keyed on `program_id` and a week window:

```
get_set_logs_for_sessions(db, program_id, user_id, since)  -> dict[int, list[WorkoutSetLog]]
get_readiness_for_sessions(db, program_id, user_id, since) -> list[UserWorkoutLog]
```

Both join through `workout_sessions`, so a log can only ever influence the program whose
session it belongs to.

### What deliberately does not change

`DELOAD_LOOKBACK_DAYS = 14` stays a **time** window, and `compute_deload_trigger` keeps
its current signature and semantics. Recent fatigue is genuinely a function of elapsed
time, not of session count — the defect was never the window, only which logs the window
could see. Fixing the sourcing without redefining the policy keeps
`test_progression_deload.py` meaningful.

`compute_adjustment`'s EWMA parameters, `MIN_SESSIONS`, and clamping range are likewise
untouched. Only its grouping key changes.

## Frontend

### Routes

```
/schedule                    SchedulePage
/sessions/:sessionId         SessionDetailPage
/sessions/:sessionId/track   WorkoutTrackingPage   (existing logger, retargeted)
/workouts/:workoutId         removed
```

Flow: dashboard card → `/sessions/:id` → `/sessions/:id/track`. The schedule is reachable
from the header nav and from the dashboard's empty state.

### Screens

**SchedulePage** — one week at a time, with prev/next navigation. `?week=` in the URL so a
week is linkable. Each row shows weekday, date, workout name, and a status badge.

Shown below for a 4-day program (offsets `[0, 1, 3, 4]` from a Monday start), viewed on
Thu 24:

```
┌─────────────────────────────────────┐
│ ◀  Week 3 of 8  ▶                   │
│                                     │
│ Mon 21  Upper Body A      ✓ done    │
│ Tue 22  Lower Body A      ✗ missed  │
│ Thu 24  Upper Body B      ● today   │
│ Fri 25  Lower Body B      ○ upcoming│
└─────────────────────────────────────┘
```

`today` and `upcoming` are not stored statuses. Both are `scheduled` rows; the UI
distinguishes them by comparing `scheduled_date` to the current date. Stored `missed`
covers past `scheduled` rows via the lazy flip.

**SessionDetailPage** — status-aware. Today or upcoming: the full exercise list with
prescriptions and a primary action (`Start workout` / `Start early`). Completed: the same
list showing actual logged weight and reps per set, no start action.

**DashboardPage** — calls `GET /schedule?start=today&end=today`. A session today renders
the existing `WorkoutCard` linking to `/sessions/:id`; anything else (rest day, program
not started, program finished, no active program) renders one neutral empty state with a
`View schedule →` link. No new endpoint is needed.

### New and removed

New: `SchedulePage`, `SessionDetailPage`, `SessionRow`, `SessionStatusBadge`,
`api/sessions.ts`, hooks `useSchedule(start, end)` and `useSession(sessionId)`.

Removed: `useWorkoutDetails.ts` and its test. Its only reason for existing is the
week-disambiguation fallback, which `session_id` makes unnecessary.

### Folded-in fixes

Both are in files this change already touches:

- `WorkoutTrackingPage.tsx:203` navigates to `/dashboard`, which is not a route — the
  dashboard is `/`. Completing a workout currently bounces through the catch-all redirect.
- `WorkoutTrackingPage.tsx` is 377 lines and gains session handling. Lift the exercise and
  set progress state into a `useSessionProgress` hook, leaving the page as layout plus
  handlers.

## Error Handling

- Session not found, or its program not owned by the caller → 404.
- `complete` on an already-completed session → idempotent no-op, 200.
- A program that was active before this change has no sessions. `/schedule` shows an
  explicit "re-activate this program to generate its schedule" state, not an empty week.
- No active program at all → `/schedule` links to program creation.

## Testing

TDD, per project convention.

**Backend**

- Offset table for `days_per_week` 1 through 7.
- Week arithmetic across a month boundary.
- Migration up and down.
- Missed-flip touches only `scheduled` rows — explicitly assert an abandoned
  `in_progress` session survives it.
- Status transitions: first set log, complete, complete-again.
- Ownership 404s on every session endpoint.
- Schedule range query returns exactly the sessions in `[start, end]`.
- `session_id` is NOT NULL on both log tables — a write without one fails.
- `compute_adjustment` treats two same-day sessions as two EWMA samples, and one session
  spanning midnight as one.
- The session-scoped signal queries never return logs from another program or user.
- `test_programs_live_signals.py` still passes: current week gets signals, adjacent weeks
  stay nominal, draft/archived/future/overrun programs get none.

**Frontend**

- Schedule week navigation and status rendering.
- The `SessionDetailPage` status variants: today, upcoming, completed.
- Dashboard card: session today vs. every other case.
- Tracking page driven by `sessionId`.

## Sequencing

One spec, three implementation phases with commit boundaries between them:

1. Backend — model, migration, materialization, missed-flip, endpoints, legacy route removal.
2. Live signals — session-scoped signal queries, `compute_adjustment` grouping.
3. Frontend — routes, screens, hooks, dashboard rewire, folded-in fixes.

Phase 2 is the riskiest: it changes inputs to the progression engine, which has its own
spec and test suite. It is sequenced after the session model exists and before the
frontend, so any engine regression surfaces against a stable backend.
