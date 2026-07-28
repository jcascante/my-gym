import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkoutCard } from '@/components/WorkoutCard';
import type { ScheduleEntry } from '@/types/session';

const entry: ScheduleEntry = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 3,
  status: 'scheduled',
  workout_id: 42,
  workout_name: 'Upper Body A',
  exercise_count: 2,
  duration_min: 45,
};

const renderCard = (onSelect = vi.fn()) => {
  render(<WorkoutCard entry={entry} programName="Push/Pull Split" onSelect={onSelect} />);
  return onSelect;
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
        entry={{ ...entry, exercise_count: 1 }}
        programName="Push/Pull Split"
        onSelect={vi.fn()}
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

  it('calls onSelect when the card is clicked', async () => {
    const onSelect = renderCard();
    await userEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('calls onSelect when activated with the keyboard', async () => {
    const onSelect = renderCard();
    await userEvent.tab();
    expect(screen.getByRole('button')).toHaveFocus();
    await userEvent.keyboard('{Enter}');
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('renders "0 exercises" when the workout has no slots', () => {
    render(
      <WorkoutCard
        entry={{ ...entry, exercise_count: 0 }}
        programName="Push/Pull Split"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('Push/Pull Split • Week 3 • 0 exercises • 45 min')).toBeInTheDocument();
  });
});
