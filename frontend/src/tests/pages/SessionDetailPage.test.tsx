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
    workoutForDate = {
      session: null,
      isRestDay: false,
      isLoading: false,
      error: new Error('boom'),
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument();
  });
});
