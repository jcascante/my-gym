import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';
import type { SessionDetail } from '@/types/session';

const navigateMock = vi.fn();
const completeSessionMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const logSessionSetMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const postSessionReadinessMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();

vi.mock('@/api/sessions', () => ({
  logSessionSet: (...args: unknown[]): Promise<unknown> => logSessionSetMock(...args),
  postSessionReadiness: (...args: unknown[]): Promise<unknown> => postSessionReadinessMock(...args),
  completeSession: (...args: unknown[]): Promise<unknown> => completeSessionMock(...args),
}));

const baseSlot = {
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

const slot = (overrides: Partial<typeof baseSlot>) => ({ ...baseSlot, ...overrides });

let sessionData: SessionDetail;

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({ data: sessionData, isLoading: false, error: null }),
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
    postSessionReadinessMock.mockClear().mockResolvedValue(undefined);
    sessionData = {
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
      slots: [slot({ workout_exercise_id: 3, exercise_name: 'Bench Press', sets: 1 })],
      logged_sets: [],
      completed_at: null,
      reactive_deload: false,
      deload_reason: null,
    };
  });

  it('renders every exercise as a section, first incomplete open by default', () => {
    sessionData.slots = [
      slot({ workout_exercise_id: 1, exercise_name: 'Bench Press', sets: 1 }),
      slot({ workout_exercise_id: 2, exercise_name: 'Row', sets: 1 }),
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText('Row')).toBeInTheDocument();
    expect(screen.getByText('Set 1')).toBeInTheDocument();
  });

  it('logs sets out of order across exercises without auto-advancing', async () => {
    sessionData.slots = [
      slot({ workout_exercise_id: 1, exercise_name: 'Bench Press', sets: 1 }),
      slot({ workout_exercise_id: 2, exercise_name: 'Row', sets: 1 }),
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /row/i }));

    const rowSection = within(screen.getByTestId('exercise-section-2'));
    await userEvent.type(rowSection.getByLabelText(/RPE \(1–10\)/), '7');
    await userEvent.click(rowSection.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() =>
      expect(logSessionSetMock).toHaveBeenCalledWith(
        9,
        expect.objectContaining({ workout_exercise_id: 2 }),
      ),
    );
    // Bench Press (still open as the seeded first-incomplete section) is untouched -
    // its own "Log Set 1" button is still there, unaffected by Row's.
    const benchSection = within(screen.getByTestId('exercise-section-1'));
    expect(benchSection.getByRole('button', { name: 'Log Set 1' })).toBeInTheDocument();
  });

  it('toggles a section open and closed on header click', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Set 1')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /bench press/i }));
    expect(screen.queryByText('Set 1')).not.toBeInTheDocument();
  });

  it('lets a logged set be corrected by tapping it', async () => {
    sessionData.logged_sets = [
      {
        id: 1,
        workout_exercise_id: 3,
        set_number: 1,
        actual_weight: 80,
        actual_reps: 8,
        actual_rpe: 7,
        effort_method: 'rpe',
      },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /set 1 logged, tap to edit/i }));
    const rpeInput = screen.getByLabelText(/RPE \(1–10\)/);
    expect((rpeInput as HTMLInputElement).value).toBe('7');

    await userEvent.clear(rpeInput);
    await userEvent.type(rpeInput, '9');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() =>
      expect(logSessionSetMock).toHaveBeenCalledWith(
        9,
        expect.objectContaining({ workout_exercise_id: 3, set_number: 1, actual_rpe: 9 }),
      ),
    );
    const setButton = await screen.findByRole('button', { name: /set 1 logged, tap to edit/i });
    expect(setButton).toBeInTheDocument();
    expect(setButton).toHaveTextContent(/set 1.*1 x 8 @80 lbs/i);
  });

  it('completes the workout immediately when every set is logged', async () => {
    sessionData.logged_sets = [
      {
        id: 1,
        workout_exercise_id: 3,
        set_number: 1,
        actual_weight: 80,
        actual_reps: 8,
        actual_rpe: 7,
        effort_method: 'rpe',
      },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    expect(screen.queryByText(/not logged/i)).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: /skip/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });

  it('confirms before completing when a set is unlogged', async () => {
    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    expect(await screen.findByText(/1 set is not logged/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(screen.queryByText(/how was that workout/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    await userEvent.click(screen.getByRole('button', { name: /finish anyway/i }));
    expect(await screen.findByText(/how was that workout/i)).toBeInTheDocument();
  });

  it('still completes the session if the readiness POST itself fails', async () => {
    postSessionReadinessMock.mockRejectedValue(new Error('network error'));
    sessionData.logged_sets = [
      {
        id: 1,
        workout_exercise_id: 3,
        set_number: 1,
        actual_weight: 80,
        actual_reps: 8,
        actual_rpe: 7,
        effort_method: 'rpe',
      },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
  });

  it('a submitted rating completes the session exactly once', async () => {
    sessionData.logged_sets = [
      {
        id: 1,
        workout_exercise_id: 3,
        set_number: 1,
        actual_weight: 80,
        actual_reps: 8,
        actual_rpe: 7,
        effort_method: 'rpe',
      },
    ];

    render(
      <MemoryRouter>
        <WorkoutTrackingPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /complete workout/i }));
    const dialogButton = await screen.findByRole('button', { name: '4' });
    await userEvent.click(dialogButton);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledWith(9));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'));
    expect(completeSessionMock).toHaveBeenCalledTimes(1);
  });
});
