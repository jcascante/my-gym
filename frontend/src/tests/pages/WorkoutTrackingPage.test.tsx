import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';

const navigateMock = vi.fn();
const completeSessionMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const logSessionSetMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();

vi.mock('@/api/sessions', () => ({
  logSessionSet: (...args: unknown[]): Promise<unknown> => logSessionSetMock(...args),
  postSessionReadiness: vi.fn().mockResolvedValue(undefined),
  completeSession: (...args: unknown[]): Promise<unknown> => completeSessionMock(...args),
}));

const slot = {
  workout_exercise_id: 3,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 1,
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

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({
    data: {
      session_id: 9,
      scheduled_date: '2026-07-27',
      week: 3,
      status: 'scheduled',
      workout_id: 4,
      workout_name: 'Upper Body B',
      exercise_count: 1,
      duration_min: 45,
      program_id: 1,
      program_name: 'My Program',
      slots: [slot],
      logged_sets: [],
      completed_at: null,
      reactive_deload: false,
      deload_reason: null,
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({ userProfile: { effort_method: 'rpe' } }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ sessionId: '9' }) };
});

describe('WorkoutTrackingPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    completeSessionMock.mockClear().mockResolvedValue({});
    logSessionSetMock.mockClear().mockResolvedValue(undefined);
  });

  it('logs the current exercise from the session slots', () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText(/Exercise 1 of 1/)).toBeInTheDocument();
  });

  it('returns to the dashboard root, not /dashboard, after completing', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    // The single slot has 1 set, so log it through SetLogger first to reach
    // exercise completion (and thus the "Complete Workout" button).
    await userEvent.type(screen.getByLabelText('RPE (1–10)'), '7');
    await userEvent.click(screen.getByRole('button', { name: /log set/i }));

    await userEvent.click(await screen.findByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });
});
