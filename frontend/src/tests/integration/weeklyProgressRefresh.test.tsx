import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '@/pages/DashboardPage';
import { getSchedule } from '@/api/sessions';
import { getActiveProgram } from '@/api/programs';
import type { SessionStatus } from '@/types/session';

vi.mock('@/api/sessions', () => ({
  getSchedule: vi.fn(),
  completeSession: vi.fn(),
  getUserStats: vi.fn().mockResolvedValue({
    workouts_this_month: 0,
    current_streak_days: 0,
    personal_records: 0,
    total_volume: 0,
    weight_unit: 'kg',
  }),
}));
vi.mock('@/api/programs', () => ({ getActiveProgram: vi.fn() }));
vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({ user: { id: 1, first_name: 'Jorge' }, userProfile: { workout_duration_min: 45 } }),
}));

// start_date is BEFORE "today" (system clock), like jorge's real account
// (started 2026-07-28, "today" is 2026-07-29) - deliberately NOT equal to
// today so it doesn't coincide with the hook's pre-load fallback of
// weekRange(today, 1).
const program = {
  program_id: 9,
  name: 'Powerlifting Strength',
  status: 'active',
  duration_weeks: 8,
  current_week: 1,
  start_date: '2026-07-28',
};

const entryAt = (date: string, status: SessionStatus) => ({
  session_id: Math.random(),
  scheduled_date: date,
  week: 1,
  status,
  workout_id: 1,
  workout_name: 'Squat Day',
  exercise_count: 3,
  duration_min: 45,
});

describe('Weekly progress refresh across navigation (real QueryClient, like main.tsx)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.setSystemTime(new Date(2026, 6, 29, 10, 0, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('reflects a newly-completed session after unmount/remount with a persistent QueryClient', async () => {
    vi.mocked(getActiveProgram).mockResolvedValue(program as never);

    // "Before completing": 0 of 4 completed.
    vi.mocked(getSchedule).mockResolvedValue([
      entryAt('2026-07-29', 'scheduled'),
      entryAt('2026-07-30', 'scheduled'),
      entryAt('2026-08-01', 'scheduled'),
      entryAt('2026-08-02', 'scheduled'),
    ]);

    // ONE persistent client for the whole test, exactly like main.tsx's singleton
    // that survives across route navigations in the real app.
    const client = new QueryClient();

    const { unmount } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText(/0 of 4 workouts completed/)).toBeInTheDocument());

    // Simulate navigating away to track a session and completing it: unmount
    // Dashboard (as React Router does on a route change) then update what the
    // backend would now return.
    unmount();
    cleanup();

    vi.mocked(getSchedule).mockResolvedValue([
      entryAt('2026-07-29', 'completed'),
      entryAt('2026-07-30', 'scheduled'),
      entryAt('2026-08-01', 'scheduled'),
      entryAt('2026-08-02', 'scheduled'),
    ]);

    // Remount Dashboard on the SAME client, simulating navigate('/') back to it.
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText(/1 of 4 workouts completed/)).toBeInTheDocument());
  });
});
