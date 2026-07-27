import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkoutCard } from '@/components/WorkoutCard';
import type { WorkoutPreview } from '@/types/program';

const makeSlot = (id: number, exerciseName: string) => ({
  workout_exercise_id: id,
  exercise_id: id,
  exercise_name: exerciseName,
  sets: 3,
  reps: 8,
  load: 135,
  rest_seconds: 90,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '2-0-1',
  warmup_sets: [],
});

const workout: WorkoutPreview = {
  workout_id: 42,
  key: 'upper-a',
  name: 'Upper Body A',
  slots: [makeSlot(1, 'Bench Press'), makeSlot(2, 'Barbell Row')],
  reactive_deload: false,
  deload_reason: null,
};

const renderCard = (onStartClick = vi.fn()) => {
  render(
    <WorkoutCard
      workout={workout}
      programName="Push/Pull Split"
      weekNumber={3}
      durationMin={45}
      onStartClick={onStartClick}
    />,
  );
  return onStartClick;
};

describe('WorkoutCard', () => {
  it('shows a TODAY eyebrow and the workout name', () => {
    renderCard();
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
  });

  it('summarises the session on one meta line', () => {
    renderCard();
    expect(screen.getByText('Push/Pull Split • Week 3 • 2 exercises • 45 min')).toBeInTheDocument();
  });

  it('singularises the exercise count', () => {
    render(
      <WorkoutCard
        workout={{ ...workout, slots: [makeSlot(1, 'Bench Press')] }}
        programName="Push/Pull Split"
        weekNumber={3}
        onStartClick={vi.fn()}
      />,
    );
    expect(screen.getByText('Push/Pull Split • Week 3 • 1 exercise • 45 min')).toBeInTheDocument();
  });

  it('does not list the exercises', () => {
    renderCard();
    expect(screen.queryByText('Bench Press')).not.toBeInTheDocument();
    expect(screen.queryByText('Barbell Row')).not.toBeInTheDocument();
    expect(screen.queryByText(/3 × 8/)).not.toBeInTheDocument();
  });

  it('is a single button whose accessible name describes the action', () => {
    renderCard();
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAccessibleName(
      'Start Upper Body A, Push/Pull Split week 3, 2 exercises, 45 minutes',
    );
  });

  it('calls onStartClick when the card is clicked', async () => {
    const onStartClick = renderCard();
    await userEvent.click(screen.getByRole('button'));
    expect(onStartClick).toHaveBeenCalledTimes(1);
  });

  it('calls onStartClick when activated with the keyboard', async () => {
    const onStartClick = renderCard();
    await userEvent.tab();
    expect(screen.getByRole('button')).toHaveFocus();
    await userEvent.keyboard('{Enter}');
    expect(onStartClick).toHaveBeenCalledTimes(1);
  });

  it('renders "0 exercises" when the workout has no slots', () => {
    render(
      <WorkoutCard
        workout={{ ...workout, slots: [] }}
        programName="Push/Pull Split"
        weekNumber={3}
        onStartClick={vi.fn()}
      />,
    );
    expect(screen.getByText('Push/Pull Split • Week 3 • 0 exercises • 45 min')).toBeInTheDocument();
  });
});
