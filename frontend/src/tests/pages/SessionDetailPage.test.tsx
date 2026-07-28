import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SessionDetailPage from '@/pages/SessionDetailPage';

const navigateMock = vi.fn();
let sessionData: unknown;

vi.mock('@/hooks/useSession', () => ({
  useSession: () => ({ data: sessionData, isLoading: false, error: null }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ sessionId: '9' }) };
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
  slots: [slot],
  logged_sets: [],
  completed_at: null,
  reactive_deload: false,
  deload_reason: null,
};

describe('SessionDetailPage', () => {
  beforeEach(() => navigateMock.mockClear());

  it('lists the prescription and offers to start a scheduled session', () => {
    sessionData = { ...base, status: 'scheduled' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Upper Body B')).toBeInTheDocument();
    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText(/4 × 8/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start workout/i })).toBeInTheDocument();
  });

  it('navigates to the tracker when starting', async () => {
    sessionData = { ...base, status: 'scheduled' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /start workout/i }));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9/track');
  });

  it('shows logged results and no start action for a completed session', () => {
    sessionData = {
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
    };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/80 × 8/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start workout/i })).not.toBeInTheDocument();
  });

  it('offers to start a future session early', () => {
    sessionData = { ...base, status: 'scheduled', scheduled_date: '2099-01-01' };

    render(
      <MemoryRouter>
        <SessionDetailPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /start early/i })).toBeInTheDocument();
  });
});
