import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '@/pages/DashboardPage';

const navigateMock = vi.fn();
let todaySession: unknown = null;
let programData: unknown = null;

vi.mock('@/hooks/useSchedule', () => ({
  useTodaySession: () => ({ session: todaySession, isLoading: false }),
}));

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      user: { id: 1, email: 'a@b.com', first_name: 'Jorge', last_name: 'C' },
      userProfile: { workout_duration_min: 45 },
    }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const entry = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 3,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 5,
  duration_min: 45,
};

describe('DashboardPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    todaySession = null;
    programData = { program_id: 1, name: 'My Program', status: 'active', duration_weeks: 8 };
  });

  it("shows today's session when one is scheduled", () => {
    todaySession = entry;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Upper Body B')).toBeInTheDocument();
  });

  it('opens the session detail in one click', async () => {
    todaySession = entry;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /Upper Body B/i }));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
  });

  it('falls back to a schedule link when nothing is scheduled today', async () => {
    todaySession = null;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/nothing scheduled today/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /view schedule/i }));
    expect(navigateMock).toHaveBeenCalledWith('/schedule');
  });

  it('prompts to create a program when there is none', () => {
    programData = null;
    todaySession = null;

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /create program/i })).toBeInTheDocument();
  });
});
