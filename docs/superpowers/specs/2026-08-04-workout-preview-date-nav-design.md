# Workout preview: prev/next day navigation

Date: 2026-08-04

## Problem

The dashboard's "today's training" card opens the workout preview page
(`SessionDetailPage`, route `/sessions/:sessionId`), which is fine on its own. But the
only way to look at a different day's workout from there is to tap "← Schedule" and go
into the weekly scheduler (`SchedulePage`, route `/schedule`) to pick another day. For the
common case of "what's tomorrow" or "what did I do two days ago," that's an unnecessary
detour through a whole other page.

The goal: let the user step forward and backward through their calendar directly from the
workout preview, without leaving it.

## Scope

In scope:

- `frontend/src/pages/SessionDetailPage.tsx` — route param changes from `sessionId` to
  `date`, gains prev/next controls, gains a "Rest day" empty state.
- A new hook (e.g. `useWorkoutForDate(date)`) in `frontend/src/hooks/useSchedule.ts` that
  resolves a date to a schedule entry, then to full session detail when one exists.
- Call sites that navigate into the preview: `frontend/src/pages/DashboardPage.tsx`
  (today's training card) and `frontend/src/components/ScheduleRow.tsx` (`onSelect`).
- `App.tsx` route definition for the preview page.
- Tests for the above.

Explicitly out of scope:

- Any change to `SchedulePage` itself (the weekly view stays as-is and remains reachable
  from primary nav).
- The `/sessions/:sessionId/track` workout-tracking route — unaffected, still session-id
  keyed.
- Backend endpoint changes, unless the `flip_missed` investigation below turns up a real
  inconsistency — if it does, that's a follow-up, not part of this spec.

## Design

### Routing

The preview route changes from `/sessions/:sessionId` to `/workout/:date` (ISO
`YYYY-MM-DD`). Date, not session id, is the natural key here: it's what both entry points
already have on hand, and it's the only key that still makes sense on a rest day, when no
session exists at all.

`DashboardPage`'s today's-training card and `ScheduleRow.onSelect` both switch from
building a `/sessions/${id}` link to `/workout/${date}` (the schedule entry already
carries `scheduled_date`).

### Data flow

New hook `useWorkoutForDate(date)`:

1. Calls `useSchedule(date, date)` (existing range endpoint, already used by
   `useTodaySession`) to get that day's `ScheduleEntry`, if any.
2. If an entry with a `session_id` comes back, calls `useSession(session_id)` (existing
   hook) to get full exercise/slot detail for rendering.
3. If no entry comes back, there's nothing further to fetch — the day is a rest day.

The hook exposes the combined loading/error state plus either the full session detail or
`null` (rest day).

### Page content

```
┌────────────────────────────────────────────┐
│  ←         Wed, Aug 5           →          │
│           Upper Body A                     │
│      Push/Pull Split · 6 exercises         │
│  [ exercise list ... ]                     │
│                              Start →       │
└────────────────────────────────────────────┘
```

- Date header replaces the current "← Schedule" button. Prev/Next are `aria-label`d
  ("Previous day" / "Next day") icon buttons on either side of the date, styled after the
  arrow pair already in `SchedulePage.tsx:60-80`.
- Tapping an arrow navigates to `/workout/<date ± 1 day>` (client-side route change, not a
  full reload — same as today's navigation between pages).
- Arrows disable at the active program's date bounds, mirroring `SchedulePage`'s
  `week <= 1` / `week >= durationWeeks` disabling. Bounds are computed from the program's
  start date and `duration_weeks` (need to confirm exact field access during
  implementation).
- **Rest day state**: when `useWorkoutForDate` resolves to no session, the page shows the
  date header + arrows with a simple "Rest day" message in place of the workout content.
  No "Start workout" button in this state.
- **Workout state**: unchanged from today — exercise list, "Start workout" / "Start early"
  button navigating to `/sessions/${session.session_id}/track`. That button still needs
  the session id, which is available once `useSession` resolves.
- The "← Schedule" link/button is removed entirely. The weekly scheduler remains reachable
  from primary navigation for users who want to jump further than a few days.

### Edge case to verify while implementing

`backend/app/crud/session.py`'s `get_session` (by id) triggers a `flip_missed` side
effect that can change a session's status. Need to confirm `get_sessions_in_range` (which
the new date-based path leans on more heavily) applies the same logic, so a session's
missed-status doesn't depend on which path resolved it. If it doesn't, that's a small
backend follow-up, not a blocker for this spec's frontend scope.

## Testing

- New/updated tests for `useWorkoutForDate`: returns session detail when an entry exists,
  returns `null` for a rest day, surfaces loading/error state.
- `SessionDetailPage` tests: renders workout content for a training day, renders "Rest
  day" for a day with no entry, prev/next arrows navigate to `date ± 1`, arrows disabled
  at program start/end bounds.
- `DashboardPage` and `ScheduleRow` tests updated to assert navigation to `/workout/:date`
  instead of `/sessions/:id`.

## Risks

Changing the preview route's param from session id to date means any existing deep link
or bookmark to `/sessions/:sessionId` stops resolving the preview page the same way.
Accepted: this app has no external deep-linking surface (no shared links, no notifications
with session-id URLs today), so the blast radius is limited to in-app navigation, which is
fully covered by the updated call sites.
