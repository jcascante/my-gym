import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExerciseSection } from './ExerciseSection';
import type { ExerciseProgress } from '../hooks/useSessionProgress';

const exercise = (overrides: Partial<ExerciseProgress> = {}): ExerciseProgress => ({
  workout_exercise_id: 1,
  exercise_id: 10,
  exercise_name: 'Bench Press',
  sets: 2,
  reps: 8,
  load: 80,
  rest_seconds: 90,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
  completedSets: [],
  ...overrides,
});

describe('ExerciseSection', () => {
  it('shows the set count and hides sets when collapsed', () => {
    render(
      <ExerciseSection
        exercise={exercise()}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen={false}
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('Bench Press')).toBeInTheDocument();
    expect(screen.getByText('0/2 sets')).toBeInTheDocument();
    expect(screen.queryByText('Set 1')).not.toBeInTheDocument();
  });

  it('shows a checkmark once every set is logged', () => {
    render(
      <ExerciseSection
        exercise={exercise({
          completedSets: [
            {
              setNumber: 1,
              weight: 80,
              reps: 8,
              effort: 8,
              effort_method: 'rpe',
              timestamp: new Date(),
            },
            {
              setNumber: 2,
              weight: 80,
              reps: 8,
              effort: 8,
              effort_method: 'rpe',
              timestamp: new Date(),
            },
          ],
        })}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen={false}
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('2/2 sets')).toBeInTheDocument();
  });

  it('calls onToggle when the header is clicked', async () => {
    const onToggle = vi.fn();
    render(
      <ExerciseSection
        exercise={exercise()}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen={false}
        onToggle={onToggle}
        onLogSet={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /bench press/i }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('renders one SetRow per set, in set order, when open', () => {
    render(
      <ExerciseSection
        exercise={exercise()}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('Set 1')).toBeInTheDocument();
    expect(screen.getByText('Set 2')).toBeInTheDocument();
  });

  it('passes the tapped set number through to onLogSet', async () => {
    const onLogSet = vi.fn().mockResolvedValue(undefined);
    render(
      <ExerciseSection
        exercise={exercise()}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen
        onToggle={vi.fn()}
        onLogSet={onLogSet}
      />,
    );

    await userEvent.type(screen.getAllByLabelText(/RPE \(1–10\)/)[1], '7');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 2' }));

    expect(onLogSet).toHaveBeenCalledWith(2, {
      weight: undefined,
      reps: undefined,
      effort: 7,
      effort_method: 'rpe',
    });
  });
});
