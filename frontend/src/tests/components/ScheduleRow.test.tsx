import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScheduleRow } from '@/components/ScheduleRow';
import { displayStatus } from '@/components/SessionStatusBadge';
import type { ScheduleEntry } from '@/types/session';

const entry: ScheduleEntry = {
  session_id: 1,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled',
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('displayStatus', () => {
  it('reads a scheduled session dated today as today', () => {
    expect(displayStatus('scheduled', '2026-07-27', '2026-07-27')).toBe('today');
  });

  it('reads a scheduled session dated later as upcoming', () => {
    expect(displayStatus('scheduled', '2026-07-31', '2026-07-27')).toBe('upcoming');
  });

  it('reads a completed session as done regardless of date', () => {
    expect(displayStatus('completed', '2026-07-20', '2026-07-27')).toBe('done');
  });

  it('reads a missed session as missed', () => {
    expect(displayStatus('missed', '2026-07-20', '2026-07-27')).toBe('missed');
  });
});

describe('ScheduleRow', () => {
  it('shows the weekday, name, and status', () => {
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={vi.fn()} />);

    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
    expect(screen.getByText(/Mon/)).toBeInTheDocument();
    expect(screen.getByText('today')).toBeInTheDocument();
  });

  it('calls onSelect with the session id when clicked', async () => {
    const onSelect = vi.fn();
    render(<ScheduleRow entry={entry} today="2026-07-27" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
