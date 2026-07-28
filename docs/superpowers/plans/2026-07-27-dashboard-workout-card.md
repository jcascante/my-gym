# Dashboard Compact Workout Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's tall today's-workout card — which lists every exercise — with a compact, single-click summary card that navigates straight to workout tracking.

**Architecture:** `WorkoutCard` is rewritten from a `Card` containing a `Button` into a single `<button>` element wrapping a `Card`. The exercise list is removed; the two emoji stat rows collapse into one dot-separated meta line. `DashboardPage` keeps its existing workout-selection logic and only adapts to the changed prop contract. `WorkoutCard`'s only consumer is `DashboardPage`, so no other call site is affected.

**Tech Stack:** React 18 + TypeScript, Tailwind CSS, Vitest + React Testing Library, run inside Docker Compose.

## Global Constraints

- Frontend-only. No backend, schema, or migration changes.
- Do not change `DashboardPage.getTodayWorkout()` — which workout is shown is out of scope.
- Do not touch the "This Week" progress bar or the four `StatCard` tiles; their hardcoded values stay.
- Do not change the loading, "No workouts scheduled for today", or "Get Started" states.
- Reuse existing typography utility classes: `display-md`, `heading-lg`, `body-sm`, `label-sm`.
- All commands run through Docker Compose, e.g. `docker-compose exec frontend npm run test`.
- Project rule (CLAUDE.md): no code comments except for non-obvious WHY.
- Commit only at task boundaries, and only when the user has approved committing.

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/components/WorkoutCard.tsx` | Modify. Becomes the compact, fully-clickable summary card. |
| `frontend/src/tests/components/WorkoutCard.test.tsx` | Create. Unit tests for the new card contract. |
| `frontend/src/pages/DashboardPage.tsx` | Modify. Call site only — no logic change. |
| `frontend/src/tests/pages/DashboardPage.test.tsx` | Modify. Update the one assertion whose text moves into the meta line. |

Task 1 delivers the component and its tests. Task 2 wires the dashboard and repairs its test. A reviewer could accept Task 1's component while rejecting Task 2's integration, so they are split.

---

### Task 1: Compact, clickable `WorkoutCard`

**Files:**
- Modify: `frontend/src/components/WorkoutCard.tsx` (full rewrite of the component body)
- Create: `frontend/src/tests/components/WorkoutCard.test.tsx`

**Interfaces:**
- Consumes: `WorkoutPreview` and `SlotPreview` from `@/types/program`; `Card` from `@/components`.
- Produces:
  ```ts
  export interface WorkoutCardProps {
    workout: WorkoutPreview;
    programName: string;
    weekNumber: number;
    durationMin?: number;   // defaults to 45
    onStartClick: () => void;  // now REQUIRED, wired to the root button's onClick
  }
  export function WorkoutCard(props: WorkoutCardProps): JSX.Element;
  ```
  Task 2 relies on `onStartClick` being required and on the meta line rendering as
  `` `${programName} • Week ${weekNumber} • ${n} exercises • ${durationMin} min` ``.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/tests/components/WorkoutCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkoutCard } from '@/components/WorkoutCard';
import type { WorkoutPreview } from '@/types/program';

const makeSlot = (id: number, exerciseName: string) => ({
  workout_exercise_id: id,
  exercise_id: id,
  exercise_name: exerciseName,
  sets: 3,
  reps: 8,
  load: 135,
  rest_seconds: 90,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '2-0-1',
  warmup_sets: [],
});

const workout: WorkoutPreview = {
  workout_id: 42,
  key: 'upper-a',
  name: 'Upper Body A',
  slots: [makeSlot(1, 'Bench Press'), makeSlot(2, 'Barbell Row')],
  reactive_deload: false,
  deload_reason: null,
};

const renderCard = (onStartClick = vi.fn()) => {
  render(
    <WorkoutCard
      workout={workout}
      programName="Push/Pull Split"
      weekNumber={3}
      durationMin={45}
      onStartClick={onStartClick}
    />,
  );
  return onStartClick;
};

describe('WorkoutCard', () => {
  it('shows a TODAY eyebrow and the workout name', () => {
    renderCard();
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
  });

  it('summarises the session on one meta line', () => {
    renderCard();
    expect(
      screen.getByText('Push/Pull Split • Week 3 • 2 exercises • 45 min'),
    ).toBeInTheDocument();
  });

  it('singularises the exercise count', () => {
    render(
      <WorkoutCard
        workout={{ ...workout, slots: [makeSlot(1, 'Bench Press')] }}
        programName="Push/Pull Split"
        weekNumber={3}
        onStartClick={vi.fn()}
      />,
    );
    expect(screen.getByText('Push/Pull Split • Week 3 • 1 exercise • 45 min')).toBeInTheDocument();
  });

  it('does not list the exercises', () => {
    renderCard();
    expect(screen.queryByText('Bench Press')).not.toBeInTheDocument();
    expect(screen.queryByText('Barbell Row')).not.toBeInTheDocument();
    expect(screen.queryByText(/3 × 8/)).not.toBeInTheDocument();
  });

  it('is a single button whose accessible name describes the action', () => {
    renderCard();
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAccessibleName('Start Upper Body A, 2 exercises, 45 minutes');
  });

  it('calls onStartClick when the card is clicked', async () => {
    const onStartClick = renderCard();
    await userEvent.click(screen.getByRole('button'));
    expect(onStartClick).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker-compose exec frontend npm run test -- --run src/tests/components/WorkoutCard.test.tsx`

Expected: FAIL. The current component renders exercise names and two buttons are not present but `getAllByRole('button')` returns the inner "Start Workout" button while the meta-line and eyebrow assertions fail on missing text.

- [ ] **Step 3: Rewrite the component**

Replace the entire contents of `frontend/src/components/WorkoutCard.tsx` with:

```tsx
import { WorkoutPreview } from '@/types/program';
import { Card } from '@/components';

export interface WorkoutCardProps {
  workout: WorkoutPreview;
  programName: string;
  weekNumber: number;
  durationMin?: number;
  onStartClick: () => void;
}

export function WorkoutCard({
  workout,
  programName,
  weekNumber,
  durationMin = 45,
  onStartClick,
}: WorkoutCardProps) {
  const exerciseCount = workout.slots.length;
  const exerciseLabel = `${exerciseCount} ${exerciseCount === 1 ? 'exercise' : 'exercises'}`;
  const meta = `${programName} • Week ${weekNumber} • ${exerciseLabel} • ${durationMin} min`;

  return (
    <button
      type="button"
      onClick={onStartClick}
      aria-label={`Start ${workout.name}, ${exerciseLabel}, ${durationMin} minutes`}
      className="block w-full text-left rounded-lg transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <Card padding="md" className="border-l-4 border-primary-600">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="label-sm text-primary-700 dark:text-primary-400 uppercase tracking-wide">
              Today
            </p>
            <h2 className="heading-lg text-neutral-900 dark:text-neutral-50 truncate">
              {workout.name}
            </h2>
            <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1 truncate">{meta}</p>
          </div>
          <span
            aria-hidden="true"
            className="shrink-0 body-sm font-medium text-primary-700 dark:text-primary-400"
          >
            Start →
          </span>
        </div>
      </Card>
    </button>
  );
}
```

Note the two behavioural changes beyond styling: `Button` is no longer imported, and
`onStartClick` lost its `?`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker-compose exec frontend npm run test -- --run src/tests/components/WorkoutCard.test.tsx`

Expected: PASS, 6 tests.

- [ ] **Step 5: Type-check and lint**

Run:
```bash
docker-compose exec frontend npm run type-check
docker-compose exec frontend npm run lint
```
Expected: both clean. `type-check` will report an error in `DashboardPage.tsx` only if that
file fails to pass `onStartClick` — it already passes it, so expect no errors here.

- [ ] **Step 6: Commit** (only if the user has approved committing)

```bash
git add frontend/src/components/WorkoutCard.tsx frontend/src/tests/components/WorkoutCard.test.tsx
git commit -m "refactor(dashboard): make WorkoutCard a compact one-click summary"
```

---

### Task 2: Dashboard integration

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx:58-68`
- Modify: `frontend/src/tests/pages/DashboardPage.test.tsx`

**Interfaces:**
- Consumes: `WorkoutCard` with the props defined in Task 1 — `onStartClick` is now required and
  the meta line reads `` `${programName} • Week ${weekNumber} • ${n} exercises • ${durationMin} min` ``.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Update the failing dashboard assertion**

`frontend/src/tests/pages/DashboardPage.test.tsx` currently asserts
`expect(screen.getByText(/My Program • Week 2/)).toBeInTheDocument();`. That text now lives in
the meta line alongside the exercise count and duration. The existing test's `makeWorkout`
helper produces workouts with `slots: []`, so the rendered meta line is
`My Program • Week 2 • 0 exercises • 45 min`.

Replace that single assertion line with:

```tsx
  expect(screen.getByText('My Program • Week 2 • 0 exercises • 45 min')).toBeInTheDocument();
```

Leave the rest of the file — the mocks, the `programData` fixture, and the
`expect(screen.getByText('Week 2 Day A')).toBeInTheDocument();` assertion — untouched. The
test's purpose (the card shows the program's current week, not always week 1) is preserved.

- [ ] **Step 2: Run the dashboard test**

Run: `docker-compose exec frontend npm run test -- --run src/tests/pages/DashboardPage.test.tsx`

Expected: PASS. `DashboardPage` already passes `onStartClick`, so no source change is needed to
make it green — this step confirms the integration rather than driving new code.

- [ ] **Step 3: Add a test that the dashboard card navigates in one click**

Append to `frontend/src/tests/pages/DashboardPage.test.tsx`:

```tsx
it('navigates to workout tracking when the card is clicked', async () => {
  programData = {
    program_id: 7,
    name: 'My Program',
    status: 'active',
    duration_weeks: 3,
    current_week: 2,
    weeks: {
      '2': [makeWorkout(2, 'Week 2 Day A')],
    },
    advisories: [],
  };

  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  await userEvent.click(screen.getByRole('button', { name: /Start Week 2 Day A/ }));

  expect(navigateMock).toHaveBeenCalledWith('/workouts/2?programId=7');
});
```

This needs three additions at the top of the file. Change the imports to:

```tsx
import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '@/pages/DashboardPage';
```

and add this mock alongside the existing `vi.mock` calls:

```tsx
const navigateMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});
```

- [ ] **Step 4: Run the dashboard test to verify both cases pass**

Run: `docker-compose exec frontend npm run test -- --run src/tests/pages/DashboardPage.test.tsx`

Expected: PASS, 2 tests. If the click test fails with `navigateMock` undefined at mock-hoist
time, move the `const navigateMock = vi.fn();` declaration above every `vi.mock` call — Vitest
hoists `vi.mock` factories, but the factory body only runs on import, so a `const` declared
before the mocks in source order is initialised in time.

- [ ] **Step 5: Run the full frontend suite, lint, and type-check**

Run:
```bash
docker-compose exec frontend npm run test -- --run
docker-compose exec frontend npm run type-check
docker-compose exec frontend npm run lint
```
Expected: all pass, no new failures. Report any pre-existing failures rather than fixing them.

- [ ] **Step 6: Verify in the running app**

Run `docker-compose up` if not already running, log in as a user with an active program, and
confirm on the dashboard that:
- the card occupies roughly one-quarter of its previous height and no exercise names appear;
- hovering anywhere on the card shows a pointer and clicking anywhere navigates to the tracking
  page for that workout;
- tabbing to the card shows a visible focus ring;
- the "This Week" and "Your Stats" sections are now visible without scrolling on a laptop
  viewport.

- [ ] **Step 7: Commit** (only if the user has approved committing)

```bash
git add frontend/src/tests/pages/DashboardPage.test.tsx
git commit -m "test(dashboard): cover one-click navigation from the workout card"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Eyebrow `TODAY`, heading, single dot-separated meta line | 1, Step 3 |
| Emoji stat rows removed | 1, Step 3 |
| Exercise list removed from the card | 1, Steps 1 & 3 |
| `border-l-4 border-primary-600` accent retained | 1, Step 3 |
| `slots` used only for `slots.length` | 1, Step 3 |
| Root is a `<button>` wrapping `Card`, no nested interactives | 1, Steps 1 & 3 |
| `onStartClick` required, wired to root `onClick` | 1, Step 3 |
| Hover / `focus-visible` styling | 1, Step 3; verified 2, Step 6 |
| `aria-label` describing the action | 1, Steps 1 & 3 |
| `→` decorative / `aria-hidden` | 1, Step 3 |
| Loading / empty / no-program states unchanged | Global constraint; `DashboardPage` untouched |
| New `WorkoutCard.test.tsx` with the four listed cases | 1, Step 1 |
| `DashboardPage.test.tsx` assertion updated to the new format | 2, Step 1 |
| Which-workout logic and placeholder sections untouched | Global constraints |

No gaps.

**Placeholder scan:** No TBDs, no "add error handling", no "similar to Task N". Every code step
carries complete code.

**Type consistency:** `WorkoutCardProps` in Task 1's Interfaces block matches the implementation
in Task 1 Step 3 and the usage assumed by Task 2. The meta-line format string is identical in
the component, the `WorkoutCard` tests, and the `DashboardPage` test assertion. `makeSlot`
returns every field of `SlotPreview` as defined in `frontend/src/types/program.ts`.
