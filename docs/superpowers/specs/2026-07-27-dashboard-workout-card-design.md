# Dashboard: compact today's-workout card

Date: 2026-07-27

## Problem

On the dashboard, the today's-workout card renders the full exercise list (name + sets × reps
+ load for every slot) above a full-width "Start Workout" button. On a program with six
exercises the card fills most of the first screen, pushing the rest of the dashboard below the
fold. The card announces the day's workout far more loudly than it needs to, and the user has
to scan a list they will see again on the tracking page anyway.

The goal: the dashboard should make it obvious that a workout is scheduled, stay visually
quiet, and take the user to workout tracking in one click.

## Scope

In scope:

- `frontend/src/components/WorkoutCard.tsx` — the only consumer is `DashboardPage`.
- The `WorkoutCard` call site in `frontend/src/pages/DashboardPage.tsx`.
- Tests for the above.

Explicitly out of scope (each is its own item):

- **Which** workout the card shows. `DashboardPage.getTodayWorkout()` returns
  `weeks[current_week][0]` — the first session of the current week, not a session chosen by
  date or completion. A user who finishes that session sees the same card again the next day.
  Fixing this needs data the API does not expose today: `ProgramPreviewOut` carries
  `current_week` but no per-workout scheduled date and no completion flag. This spec keeps the
  existing selection logic untouched.
- The "This Week" progress bar (hardcoded `completed={0} total={5}`) and the four stat tiles
  (hardcoded zeros). They are placeholder data and stay as-is.
- Backend changes of any kind.

## Design

### Card content

The card drops to a summary. Everything the user needs to decide "yes, that's today's
session" and nothing more:

```
┌────────────────────────────────────────────┐
│ TODAY                                      │
│ Upper Body A                               │
│ Push/Pull Split · Wk 3 · 6 exercises · 45m │
│                                   Start →  │
└────────────────────────────────────────────┘
```

- **Eyebrow** — `TODAY`, uppercase, `label-sm`, muted.
- **Heading** — `workout.name`.
- **Meta line** — one dot-separated row: program name, week number, exercise count, duration.
  This replaces the two emoji stat rows (`📋` exercises, `⏱️` duration); the emoji are dropped.
- **Affordance** — a "Start →" cue aligned to the end of the card. It is a visual cue, not a
  separate interactive element (see below).
- The `workout.slots.map(...)` exercise list is removed from the card entirely. The tracking
  page remains the place to see exercises.
- The `border-l-4 border-primary-600` left accent stays. It is the "there is a workout today"
  signal — present without being loud.

`slots` is still read, but only for `slots.length`.

### Interaction

The card root becomes a single clickable surface: a `<button type="button">` wrapping the
`Card`, rather than a `Card` containing a `Button`.

- One tap target covering the whole card — better on mobile than a small button.
- One focus stop, and no interactive element nested inside another interactive element.
- `onStartClick` becomes a required prop and is wired to the root `onClick`.
- Hover and `focus-visible` styling on the card surface.

### Accessibility

- `aria-label` on the root button describing the action and the summary, e.g.
  `"Start Upper Body A, 6 exercises, 45 minutes"`, so screen-reader users get the same summary
  the meta line gives sighted users without the dot separators being read as punctuation noise.
- The `→` is decorative (`aria-hidden`).

### Unchanged states

These render as they do today; only the populated card changes:

- Loading — spinner card with "Loading workout...".
- Active program, no workout for the current week — "No workouts scheduled for today."
- No active program — the "Get Started" card with a "Create Program" button.

## Testing

New `frontend/src/tests/components/WorkoutCard.test.tsx`:

- renders the workout name and the meta line (program, week, exercise count, duration);
- does **not** render any exercise name from `slots`;
- calls `onStartClick` when the card is clicked;
- exposes an accessible name covering the workout.

Existing `frontend/src/tests/pages/DashboardPage.test.tsx` (currently untracked) asserts
`/My Program • Week 2/`. That text moves into the new meta line, so the assertion is updated to
match the new format. The test's intent — the card shows the program's current week rather than
always week 1 — is preserved.

## Risks

Removing the exercise list means a user cannot preview the day's exercises without navigating.
Accepted: the tracking page is one click away and shows the full list, and the preview was the
main source of the card's bulk.
