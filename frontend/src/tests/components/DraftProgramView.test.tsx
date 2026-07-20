import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DraftProgramView } from '@/components/DraftProgramView';

vi.mock('@/hooks/usePrograms', () => ({
  useSubmitFeedback: () => ({ mutate: vi.fn(), isPending: false }),
  useSlotAlternatives: () => ({ data: [], isLoading: false }),
  programKeys: { preview: (id: number) => ['program', id] },
}));

vi.mock('@/hooks/useExercises', () => ({
  useExercises: () => ({ data: [], isLoading: false }),
}));

const program = {
  program_id: 1,
  name: 'P',
  status: 'draft' as const,
  duration_weeks: 2,
  weeks: {
    '1': [
      {
        workout_id: 1,
        key: 'a',
        name: 'Day A',
        slots: [
          {
            workout_exercise_id: 9,
            exercise_id: 3,
            exercise_name: 'Barbell Squat',
            sets: 3,
            reps: 5,
            load: 60,
            rest_seconds: 120,
            note: null,
            is_locked: true,
            is_user_swapped: false,
            effort_target: null,
            rotation_pool: [],
            tempo: 'controlled',
            warmup_sets: [],
          },
        ],
      },
    ],
    '2': [],
  },
  advisories: [],
};

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

it('shows session, slot, and locked badge', () => {
  render(wrap(<DraftProgramView program={program} programId={1} />));
  expect(screen.getByText('Day A')).toBeInTheDocument();
  expect(screen.getByText(/3 × 5/)).toBeInTheDocument();
  expect(screen.getByLabelText(/locked/i)).toBeInTheDocument();
});

it('renders draft-level advisories after the header', () => {
  const programWithAdvisories = {
    ...program,
    advisories: [
      {
        code: 'vol-low',
        severity: 'info' as const,
        message: 'Hamstrings below MEV for hypertrophy.',
        subject: 'hamstrings',
      },
    ],
  };
  render(wrap(<DraftProgramView program={programWithAdvisories} programId={1} />));
  expect(screen.getByRole('alert')).toBeInTheDocument();
  expect(screen.getByText('Hamstrings below MEV for hypertrophy.')).toBeInTheDocument();
});

it('does not render advisories section when array is empty', () => {
  render(wrap(<DraftProgramView program={program} programId={1} />));
  const alerts = screen.queryAllByRole('alert');
  expect(alerts).toHaveLength(0);
});
