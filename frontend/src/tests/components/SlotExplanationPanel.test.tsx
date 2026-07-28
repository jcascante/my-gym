import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SlotExplanationPanel } from '@/components/SlotExplanationPanel';
import type { SlotExplanation } from '@/types/explain';

let explanationState: {
  data: SlotExplanation | undefined;
  isLoading: boolean;
  isError: boolean;
} = {
  data: undefined,
  isLoading: false,
  isError: false,
};

vi.mock('@/hooks/useExplain', () => ({
  useSlotExplanation: () => explanationState,
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  explanationState = { data: undefined, isLoading: false, isError: false };
});

it('starts collapsed, showing only the toggle', () => {
  render(wrap(<SlotExplanationPanel programId={1} workoutExerciseId={9} />));
  expect(screen.getByText('Why this exercise?')).toBeInTheDocument();
  expect(screen.queryByText('Volume contribution')).not.toBeInTheDocument();
});

it('renders factors and ledger contributions once expanded and loaded', () => {
  explanationState = {
    data: {
      workout_exercise_id: 9,
      exercise_id: 3,
      exercise_name: 'Barbell Back Squat',
      factors: { variety: 1.0, muscle_fit: 0.5 },
      score: 0.8,
      ledger_contributions: [{ group: 'quads', effective_sets: 3.0 }],
      safety_note: null,
    },
    isLoading: false,
    isError: false,
  };
  render(wrap(<SlotExplanationPanel programId={1} workoutExerciseId={9} />));
  fireEvent.click(screen.getByText('Why this exercise?'));

  expect(screen.getByText('Hide why')).toBeInTheDocument();
  expect(screen.getByText('variety')).toBeInTheDocument();
  expect(screen.getByText('100%')).toBeInTheDocument();
  expect(screen.getByText('Volume contribution')).toBeInTheDocument();
  expect(screen.getByText('quads')).toBeInTheDocument();
  expect(screen.getByText('3.0 sets')).toBeInTheDocument();
});

it('renders the safety note as an info alert when present', () => {
  explanationState = {
    data: {
      workout_exercise_id: 9,
      exercise_id: 3,
      exercise_name: 'Barbell Back Squat',
      factors: {},
      score: 0.8,
      ledger_contributions: [],
      safety_note: 'This exercise carries a contraindication tag.',
    },
    isLoading: false,
    isError: false,
  };
  render(wrap(<SlotExplanationPanel programId={1} workoutExerciseId={9} />));
  fireEvent.click(screen.getByText('Why this exercise?'));

  expect(screen.getByText('This exercise carries a contraindication tag.')).toBeInTheDocument();
});

it('does not render a volume-contribution section when there are none', () => {
  explanationState = {
    data: {
      workout_exercise_id: 9,
      exercise_id: 3,
      exercise_name: 'Barbell Back Squat',
      factors: {},
      score: 0.8,
      ledger_contributions: [],
      safety_note: null,
    },
    isLoading: false,
    isError: false,
  };
  render(wrap(<SlotExplanationPanel programId={1} workoutExerciseId={9} />));
  fireEvent.click(screen.getByText('Why this exercise?'));

  expect(screen.queryByText('Volume contribution')).not.toBeInTheDocument();
});

it('shows an error message when the explanation fails to load', () => {
  explanationState = { data: undefined, isLoading: false, isError: true };
  render(wrap(<SlotExplanationPanel programId={1} workoutExerciseId={9} />));
  fireEvent.click(screen.getByText('Why this exercise?'));
  expect(screen.getByText(/Couldn't load an explanation/)).toBeInTheDocument();
});
