# Workout Preview Prev/Next Day Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user step forward/backward through their calendar directly from the workout preview page, without detouring through the weekly scheduler.

**Architecture:** The preview page (`SessionDetailPage`) moves from a session-id-keyed route (`/sessions/:sessionId`) to a date-keyed route (`/workout/:date`). A new hook, `useWorkoutForDate`, resolves a date to a schedule entry and then to full session detail when one exists, or reports a rest day when it doesn't. Prev/Next arrows on the page increment/decrement the date in the URL, disabled at the active program's date bounds.

**Tech Stack:** React + TypeScript, React Router, TanStack Query (`@tanstack/react-query`), Vitest + Testing Library.

## Global Constraints

- TDD: write the failing test before the implementation, for every task (per project CLAUDE.md).
- No backend changes. `get_sessions_in_range` (`backend/app/crud/session.py:31-60`) already calls `flip_missed` per program before returning results, same as `get_session` (by id) — confirmed during design, both paths keep missed-status consistent, so the "verify during implementation" edge case in the design spec is resolved with no backend follow-up needed.
- Follow existing code style: no comments except non-obvious WHY; Tailwind utility classes matching the surrounding page; `Button`/`Card`/`Alert`/`Spinner`/`SessionStatusBadge` come from the `@/components` barrel, not individual files.
- Design spec: `docs/superpowers/specs/2026-08-04-workout-preview-date-nav-design.md`.

---

### Task 1: Date-math helpers — `addDays` and `programDateBounds`

**Files:**
- Modify: `frontend/src/hooks/useSchedule.ts`
- Test: `frontend/src/tests/hooks/useSchedule.test.tsx`

**Interfaces:**
- Consumes: existing `toIsoDate(d: Date): string` and `weekRange(startDate: string, week: number): { start: string; end: string }`, both already in `frontend/src/hooks/useSchedule.ts`.
- Produces (new exports from `frontend/src/hooks/useSchedule.ts`):
  - `addDays(dateStr: string, delta: number): string` — returns the ISO date `delta` days from `dateStr` (delta may be negative).
  - `programDateBounds(startDate: string, durationWeeks: number): { start: string; end: string }` — returns the program's first and last calendar day.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/tests/hooks/useSchedule.test.tsx`, after the existing `toIsoDate` import line, add `addDays, programDateBounds` to the import list:

```ts
import {
  useSchedule,
  useTodaySession,
  useWeeklyProgress,
  useUserStats,
  toIsoDate,
  addDays,
  programDateBounds,
} from '@/hooks/useSchedule';
```

Then append these two `describe` blocks at the end of the file:

```tsx
describe('addDays', () => {
  it('adds days forward, including across a month boundary', () => {
    expect(addDays('2026-07-31', 1)).toBe('2026-08-01');
  });

  it('subtracts days backward, including across a month boundary', () => {
    expect(addDays('2026-08-01', -1)).toBe('2026-07-31');
  });
});

describe('programDateBounds', () => {
  it('spans from the start date through the end of the final week', () => {
    expect(programDateBounds('2026-07-01', 2)).toEqual({ start: '2026-07-01', end: '2026-07-14' });
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/hooks/useSchedule.test.tsx`
Expected: FAIL — `addDays` and `programDateBounds` are not exported from `@/hooks/useSchedule`.

- [ ] **Step 3: Implement the helpers**

In `frontend/src/hooks/useSchedule.ts`, add after the existing `weekRange` function (after line 25):

```ts
export function addDays(dateStr: string, delta: number): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  return toIsoDate(new Date(y, m - 1, d + delta));
}

export function programDateBounds(
  startDate: string,
  durationWeeks: number,
): { start: string; end: string } {
  return { start: startDate, end: weekRange(startDate, durationWeeks).end };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/hooks/useSchedule.test.tsx`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSchedule.ts frontend/src/tests/hooks/useSchedule.test.tsx
git commit -m "feat: add addDays and programDateBounds date helpers"
```

---

### Task 2: `useWorkoutForDate` hook

**Files:**
- Modify: `frontend/src/hooks/useSession.ts`
- Create: `frontend/src/tests/hooks/useSession.test.tsx`

**Interfaces:**
- Consumes: `useSchedule(start: string, end: string)` from `frontend/src/hooks/useSchedule.ts` (returns a TanStack Query result over `ScheduleEntry[]`); existing `useSession(sessionId: number | null)` in the same file; `SessionDetail` type from `@/types/session`.
- Produces (new export from `frontend/src/hooks/useSession.ts`):
  - `useWorkoutForDate(date: string): { session: SessionDetail | null; isRestDay: boolean; isLoading: boolean; error: unknown }`

**Why this hook lives in `useSession.ts` and not `useSchedule.ts`:** `useSession.ts` already imports `sessionKeys` from `useSchedule.ts`. Putting the composing hook in `useSchedule.ts` instead would require `useSchedule.ts` to import `useSession.ts`, creating a circular import between the two files.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/tests/hooks/useSession.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useWorkoutForDate } from '@/hooks/useSession';
import { getSchedule, getSession } from '@/api/sessions';

vi.mock('@/api/sessions', () => ({ getSchedule: vi.fn(), getSession: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const entry = {
  session_id: 9,
  scheduled_date: '2026-08-05',
  week: 3,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 5,
  duration_min: 45,
};

const detail = {
  ...entry,
  program_id: 1,
  program_name: 'My Program',
  weight_unit: 'kg' as const,
  slots: [],
  logged_sets: [],
  completed_at: null,
  reactive_deload: false,
  deload_reason: null,
};

describe('useWorkoutForDate', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns the full session detail for a training day', async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);
    vi.mocked(getSession).mockResolvedValue(detail);

    const { result } = renderHook(() => useWorkoutForDate('2026-08-05'), { wrapper });

    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.session?.session_id).toBe(9);
    expect(result.current.isRestDay).toBe(false);
    expect(getSession).toHaveBeenCalledWith(9);
  });

  it('reports a rest day and skips the session fetch when nothing is scheduled', async () => {
    vi.mocked(getSchedule).mockResolvedValue([]);

    const { result } = renderHook(() => useWorkoutForDate('2026-08-06'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isRestDay).toBe(true);
    expect(result.current.session).toBeNull();
    expect(getSession).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/hooks/useSession.test.tsx`
Expected: FAIL — `useWorkoutForDate` is not exported from `@/hooks/useSession`.

- [ ] **Step 3: Implement the hook**

Replace the full contents of `frontend/src/hooks/useSession.ts` with:

```ts
import { useQuery } from '@tanstack/react-query';
import { getSession } from '@/api/sessions';
import { sessionKeys, useSchedule } from '@/hooks/useSchedule';
import type { SessionDetail } from '@/types/session';

export function useSession(sessionId: number | null) {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId ?? 0),
    queryFn: () => getSession(sessionId as number),
    enabled: sessionId !== null,
  });
}

export interface WorkoutForDate {
  session: SessionDetail | null;
  isRestDay: boolean;
  isLoading: boolean;
  error: unknown;
}

export function useWorkoutForDate(date: string): WorkoutForDate {
  const {
    data: entries,
    isLoading: scheduleLoading,
    error: scheduleError,
  } = useSchedule(date, date);
  const entrySessionId = entries?.[0]?.session_id ?? null;
  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSession(entrySessionId);

  return {
    session: session ?? null,
    isRestDay: !scheduleLoading && entrySessionId === null,
    isLoading: scheduleLoading || sessionLoading,
    error: scheduleError ?? sessionError ?? null,
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/hooks/useSession.test.tsx`
Expected: PASS, both tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSession.ts frontend/src/tests/hooks/useSession.test.tsx
git commit -m "feat: add useWorkoutForDate hook resolving a date to session detail or rest day"
```

---

### Task 3: Rewrite `SessionDetailPage` for date-based routing, prev/next, and rest days

**Files:**
- Modify: `frontend/src/pages/SessionDetailPage.tsx`
- Modify: `frontend/src/tests/pages/SessionDetailPage.test.tsx`

**Interfaces:**
- Consumes: `useWorkoutForDate(date: string)` (Task 2); `addDays`, `programDateBounds`, `toIsoDate` from `frontend/src/hooks/useSchedule.ts` (Task 1 + existing); `useActiveProgram()` from `frontend/src/hooks/usePrograms.ts` (existing, returns a TanStack Query result over a `ProgramPreview`-shaped object with `start_date?: string | null` and `duration_weeks: number`).
- Produces: `SessionDetailPage` default export, now rendered at route `/workout/:date` (wired in Task 4) instead of `/sessions/:sessionId`.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `frontend/src/tests/pages/SessionDetailPage.test.tsx` with:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SessionDetailPage from '@/pages/SessionDetailPage';

const navigateMock = vi.fn();
let workoutForDate: {
  session: unknown;
  isRestDay: boolean;
  isLoading: boolean;
  error: unknown;
};
let programData: unknown;

vi.mock('@/hooks/useSession', () => ({
  useWorkoutForDate: () => workoutForDate,
}));

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ date: '2026-07-27' }) };
});

const slot = {
  workout_exercise_id: 3,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 4,
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

const base = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 3,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 1,
  duration_min: 45,
  program_id: 1,
  program_name: 'My Program',
  weight_unit: 'kg',
  slots: [slot],
  logged_sets: [],
  completed_at: null,
  reactive_deload: false,
  deload_reason: null,
};

describe('SessionDetailPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    programData = { start_date: '2026-07-01', duration_weeks: 8 };
  });

  it('lists the prescription and offers to start a scheduled session', () => {
    workoutForDate = {
      session: { ...base, status: 'scheduled' },
      isRestDay: false,
      isLoading: false,
      error: null,
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Upper Body B')).toBeInTheDocument();
    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText('4 x 8 @80 kg')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start workout/i })).toBeInTheDocument();
  });

  it('navigates to the tracker when starting', async () => {
    workoutForDate = {
      session: { ...base, status: 'scheduled' },
      isRestDay: false,
      isLoading: false,
      error: null,
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /start workout/i }));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9/track');
  });

  it('shows logged results and no start action for a completed session', () => {
    workoutForDate = {
      session: {
        ...base,
        status: 'completed',
        logged_sets: [
          {
            id: 1,
            workout_exercise_id: 3,
            set_number: 1,
            actual_weight: 80,
            actual_reps: 8,
            actual_rpe: 8,
            effort_method: 'rpe',
          },
        ],
      },
      isRestDay: false,
      isLoading: false,
      error: null,
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('1 x 8 @80 kg')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start workout/i })).not.toBeInTheDocument();
  });

  it('offers to start a future session early', () => {
    workoutForDate = {
      session: { ...base, status: 'scheduled', scheduled_date: '2099-01-01' },
      isRestDay: false,
      isLoading: false,
      error: null,
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /start early/i })).toBeInTheDocument();
  });

  it('shows a rest day placeholder when nothing is scheduled', () => {
    workoutForDate = { session: null, isRestDay: true, isLoading: false, error: null };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/rest day/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start workout/i })).not.toBeInTheDocument();
  });

  it('navigates to the previous day', async () => {
    workoutForDate = { session: null, isRestDay: true, isLoading: false, error: null };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /previous day/i }));

    expect(navigateMock).toHaveBeenCalledWith('/workout/2026-07-26');
  });

  it('navigates to the next day', async () => {
    workoutForDate = { session: null, isRestDay: true, isLoading: false, error: null };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /next day/i }));

    expect(navigateMock).toHaveBeenCalledWith('/workout/2026-07-28');
  });

  it('disables the previous-day arrow at the start of the program', () => {
    programData = { start_date: '2026-07-27', duration_weeks: 8 };
    workoutForDate = { session: null, isRestDay: true, isLoading: false, error: null };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /previous day/i })).toBeDisabled();
  });

  it('disables the next-day arrow at the end of the program', () => {
    programData = { start_date: '2026-07-21', duration_weeks: 1 };
    workoutForDate = { session: null, isRestDay: true, isLoading: false, error: null };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /next day/i })).toBeDisabled();
  });

  it('shows an error state when the workout fails to load', () => {
    workoutForDate = { session: null, isRestDay: false, isLoading: false, error: new Error('boom') };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/pages/SessionDetailPage.test.tsx`
Expected: FAIL — the current page reads `useParams<{ sessionId }>()` and calls `useSession`, not `useWorkoutForDate`/`useParams<{ date }>()`; rest-day and prev/next arrow assertions have nothing to match yet.

- [ ] **Step 3: Rewrite the page**

Replace the full contents of `frontend/src/pages/SessionDetailPage.tsx` with:

```tsx
import { useNavigate, useParams } from 'react-router-dom';
import { useWorkoutForDate } from '@/hooks/useSession';
import { useActiveProgram } from '@/hooks/usePrograms';
import { toIsoDate, addDays, programDateBounds } from '@/hooks/useSchedule';
import { Alert, Button, Card, SessionStatusBadge, Spinner } from '@/components';
import { formatEffortDisplay } from '@/utils/effortDisplay';
import type { LoggedSet } from '@/types/session';
import type { EffortTarget } from '@/types/program';

export default function SessionDetailPage() {
  const navigate = useNavigate();
  const { date } = useParams<{ date: string }>();
  const currentDate = date ?? toIsoDate(new Date());

  const { data: program } = useActiveProgram();
  const { session, isLoading, error } = useWorkoutForDate(currentDate);

  if (isLoading) return <Spinner />;

  if (error) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-4">
        <Card padding="lg" className="text-center">
          <p className="body-md text-error-600 mb-4">This workout could not be loaded.</p>
          <Button onClick={() => navigate('/schedule')}>Back to schedule</Button>
        </Card>
      </div>
    );
  }

  const today = toIsoDate(new Date());
  const startDate = program?.start_date ?? today;
  const bounds = programDateBounds(startDate, program?.duration_weeks ?? 1);
  const prevDisabled = currentDate <= bounds.start;
  const nextDisabled = currentDate >= bounds.end;

  const [y, m, d] = currentDate.split('-').map(Number);
  const dateLabel = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const isDone = session?.status === 'completed';
  const isFuture = session ? session.scheduled_date > today : false;
  const canStart = session ? !isDone && session.status !== 'skipped' : false;

  const setsFor = (workoutExerciseId: number): LoggedSet[] =>
    (session?.logged_sets ?? [])
      .filter((s) => s.workout_exercise_id === workoutExerciseId)
      .sort((a, b) => a.set_number - b.set_number);

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4 pb-28">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="secondary"
            aria-label="Previous day"
            disabled={prevDisabled}
            onClick={() => navigate(`/workout/${addDays(currentDate, -1)}`)}
          >
            ←
          </Button>
          <div className="text-center">
            <p className="label-sm text-neutral-600 dark:text-neutral-400">
              {dateLabel}
              {session && ` • Week ${session.week}`}
            </p>
            {session && (
              <SessionStatusBadge
                status={session.status}
                scheduledDate={session.scheduled_date}
                today={today}
              />
            )}
          </div>
          <Button
            variant="secondary"
            aria-label="Next day"
            disabled={nextDisabled}
            onClick={() => navigate(`/workout/${addDays(currentDate, 1)}`)}
          >
            →
          </Button>
        </div>

        {!session ? (
          <Card padding="lg" className="text-center">
            <p className="body-md text-neutral-600 dark:text-neutral-400">Rest day</p>
          </Card>
        ) : (
          <>
            <div className="mb-6">
              <h1 className="display-md">{session.workout_name}</h1>
              <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {session.program_name} • {session.exercise_count} exercises • {session.duration_min} min
              </p>
            </div>

            {session.reactive_deload && session.deload_reason && (
              <Alert type="info" className="mb-4">
                {session.deload_reason}
              </Alert>
            )}

            <Card padding="md">
              <ol className="divide-y divide-neutral-200 dark:divide-neutral-700">
                {session.slots.map((slot, index) => {
                  const logged = setsFor(slot.workout_exercise_id);
                  return (
                    <li
                      key={slot.workout_exercise_id}
                      className="py-3 flex items-baseline justify-between gap-4"
                    >
                      <span className="body-md text-neutral-900 dark:text-neutral-50">
                        {index + 1}. <span>{slot.exercise_name}</span>
                      </span>
                      <span className="body-sm text-neutral-600 dark:text-neutral-400 text-right">
                        {logged.length > 0
                          ? logged
                              .map((s) => {
                                const effortTarget: EffortTarget | null = s.effort_method
                                  ? {
                                      method: s.effort_method as EffortTarget['method'],
                                      value: s.actual_rpe ?? undefined,
                                    }
                                  : null;
                                return formatEffortDisplay(
                                  1,
                                  s.actual_reps ?? 0,
                                  s.actual_weight ?? null,
                                  session.weight_unit,
                                  effortTarget,
                                );
                              })
                              .join('  ')
                          : formatEffortDisplay(
                              slot.sets,
                              slot.reps,
                              slot.load,
                              session.weight_unit,
                              slot.effort_target,
                            )}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </Card>
          </>
        )}
      </div>

      {canStart && session && (
        <div className="fixed bottom-0 left-0 right-0 px-4 pb-4 bg-gradient-to-t from-neutral-50 dark:from-neutral-900">
          <div className="max-w-2xl mx-auto">
            <Button
              className="w-full"
              onClick={() => navigate(`/sessions/${session.session_id}/track`)}
            >
              {isFuture ? 'Start early' : 'Start workout'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

The page only destructures `session`, `isLoading`, and `error` from the hook — `isRestDay` is redundant for rendering since `!session` already covers the rest-day branch (and stays correct even while `isRestDay` is momentarily out of sync during the loading transition).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/pages/SessionDetailPage.test.tsx`
Expected: PASS, all eleven tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SessionDetailPage.tsx frontend/src/tests/pages/SessionDetailPage.test.tsx
git commit -m "feat: date-based workout preview with prev/next day navigation and rest days"
```

---

### Task 4: Switch the preview route from session id to date

**Files:**
- Modify: `frontend/src/App.tsx:69`

**Interfaces:**
- Consumes: `SessionDetailPage` default export (Task 3), now expecting a `date` route param.
- Produces: route `/workout/:date` registered; `/sessions/:sessionId` (preview) route removed. `/sessions/:sessionId/track` (line 66, `WorkoutTrackingPage`) is untouched.

- [ ] **Step 1: Update the route**

In `frontend/src/App.tsx`, change line 69 from:

```tsx
            <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
```

to:

```tsx
            <Route path="/workout/:date" element={<SessionDetailPage />} />
```

- [ ] **Step 2: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: `SessionDetailPage.test.tsx` and `useSession.test.tsx`/`useSchedule.test.tsx` still PASS (they mock `useParams`/hooks directly and don't depend on route registration). `DashboardPage.test.tsx` and `SchedulePage.test.tsx`/`ScheduleRow.test.tsx` are expected to FAIL at this point — their `navigateMock` assertions still expect `/sessions/:id` until Tasks 5 and 6 update them. Confirm the only failures are in those four files, for the reason above, before proceeding.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: route the workout preview page by date instead of session id"
```

---

### Task 5: Update the dashboard's today's-training card to navigate by date

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx:63`
- Modify: `frontend/src/tests/pages/DashboardPage.test.tsx:79`

**Interfaces:**
- Consumes: route `/workout/:date` (Task 4); `todaySession: ScheduleEntry` (existing, from `useTodaySession()`), which already carries `scheduled_date: string`.
- Produces: n/a (leaf call site).

- [ ] **Step 1: Update the failing test**

In `frontend/src/tests/pages/DashboardPage.test.tsx`, change line 79 from:

```ts
    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
```

to:

```ts
    expect(navigateMock).toHaveBeenCalledWith('/workout/2026-07-27');
```

(`2026-07-27` is `entry.scheduled_date` defined at the top of that test file.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/tests/pages/DashboardPage.test.tsx`
Expected: FAIL on the `'opens the session detail in one click'` test — actual call is still `/sessions/9`.

- [ ] **Step 3: Update the call site**

In `frontend/src/pages/DashboardPage.tsx`, change line 63 from:

```tsx
              onSelect={() => navigate(`/sessions/${todaySession.session_id}`)}
```

to:

```tsx
              onSelect={() => navigate(`/workout/${todaySession.scheduled_date}`)}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/tests/pages/DashboardPage.test.tsx`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx frontend/src/tests/pages/DashboardPage.test.tsx
git commit -m "feat: navigate to the workout preview by date from the dashboard card"
```

---

### Task 6: Update the scheduler's row selection to navigate by date

**Files:**
- Modify: `frontend/src/components/ScheduleRow.tsx`
- Modify: `frontend/src/pages/SchedulePage.tsx:93`
- Modify: `frontend/src/tests/components/ScheduleRow.test.tsx:46-53`
- Modify: `frontend/src/tests/pages/SchedulePage.test.tsx:85-95`

**Interfaces:**
- Consumes: route `/workout/:date` (Task 4).
- Produces: `ScheduleRowProps.onSelect` signature changes from `(sessionId: number) => void` to `(scheduledDate: string) => void`. `ScheduleRow` has no other consumers besides `SchedulePage` (confirmed during design research), so this is a safe signature change.

- [ ] **Step 1: Update the failing tests**

In `frontend/src/tests/components/ScheduleRow.test.tsx`, change the `'calls onSelect...'` test (lines 46-53) from:

```tsx
  it('calls onSelect with the session id when clicked', async () => {
    const onSelect = vi.fn();
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledWith(1);
  });
```

to:

```tsx
  it('calls onSelect with the scheduled date when clicked', async () => {
    const onSelect = vi.fn();
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledWith('2026-07-27');
  });
```

In `frontend/src/tests/pages/SchedulePage.test.tsx`, change the `'navigates to the session detail on select'` test (lines 85-95) from:

```tsx
  it('navigates to the session detail on select', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByText('Upper Body A'));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
  });
```

to:

```tsx
  it('navigates to the workout preview on select', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByText('Upper Body A'));

    expect(navigateMock).toHaveBeenCalledWith('/workout/2026-07-27');
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/components/ScheduleRow.test.tsx src/tests/pages/SchedulePage.test.tsx`
Expected: FAIL on both updated tests — current code still calls `onSelect`/`navigate` with the numeric session id.

- [ ] **Step 3: Update `ScheduleRow`**

In `frontend/src/components/ScheduleRow.tsx`, change the props interface (lines 4-8) from:

```tsx
export interface ScheduleRowProps {
  entry: ScheduleEntry;
  today: string;
  onSelect: (sessionId: number) => void;
}
```

to:

```tsx
export interface ScheduleRowProps {
  entry: ScheduleEntry;
  today: string;
  onSelect: (scheduledDate: string) => void;
}
```

And change line 20 from:

```tsx
      onClick={() => onSelect(entry.session_id)}
```

to:

```tsx
      onClick={() => onSelect(entry.scheduled_date)}
```

- [ ] **Step 4: Update `SchedulePage`'s call site**

In `frontend/src/pages/SchedulePage.tsx`, change line 93 from:

```tsx
                  onSelect={(id) => navigate(`/sessions/${id}`)}
```

to:

```tsx
                  onSelect={(date) => navigate(`/workout/${date}`)}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/components/ScheduleRow.test.tsx src/tests/pages/SchedulePage.test.tsx`
Expected: PASS, all tests in both files.

- [ ] **Step 6: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: PASS, no failures anywhere (this is the point where Task 4's expected interim failures should now be resolved).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ScheduleRow.tsx frontend/src/pages/SchedulePage.tsx frontend/src/tests/components/ScheduleRow.test.tsx frontend/src/tests/pages/SchedulePage.test.tsx
git commit -m "feat: navigate to the workout preview by date from the schedule row"
```

---

### Task 7: Type-check and lint

**Files:** none (verification only)

- [ ] **Step 1: Run the TypeScript compiler**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. Pay particular attention to `SessionDetailPage.tsx` — `session` is `SessionDetail | null` throughout, and every place it's read outside the `!session` guard must be within the branch where TypeScript has narrowed it to non-null (the `session.workout_name`/`session.slots`/etc. block, and the `canStart && session` guard on the "Start workout" button).

- [ ] **Step 2: Run the linter**

Run: `cd frontend && npx eslint src/pages/SessionDetailPage.tsx src/pages/DashboardPage.tsx src/pages/SchedulePage.tsx src/components/ScheduleRow.tsx src/hooks/useSchedule.ts src/hooks/useSession.ts src/App.tsx`
Expected: no errors.

- [ ] **Step 3: Commit any fixes**

If Steps 1 or 2 required changes:

```bash
git add -A
git commit -m "fix: resolve type/lint issues from workout preview date navigation"
```

If no changes were needed, skip this step.

---

## Self-Review Notes

- **Spec coverage:** calendar-day granularity with rest-day state (Task 3), removal of the "← Schedule" link (Task 3, replaced by date header + arrows), date-bounded prev/next mirroring `SchedulePage`'s week-bounds pattern (Task 1 + Task 3), all three entry points updated to the new route (Tasks 4-6), the `flip_missed` edge case investigated and resolved with no backend changes (Global Constraints) — all covered.
- **Placeholder scan:** no TBDs; every step shows full code, not descriptions of code.
- **Type consistency:** `useWorkoutForDate` returns `{ session: SessionDetail | null; isRestDay: boolean; isLoading: boolean; error: unknown }` in Task 2 and is consumed with exactly that shape in Task 3's test mocks and page code. `ScheduleRowProps.onSelect` changes from `(sessionId: number) => void` to `(scheduledDate: string) => void` consistently across Task 6's component, call site, and both test files.
