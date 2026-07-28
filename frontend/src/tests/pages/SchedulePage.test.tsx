import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SchedulePage from '@/pages/SchedulePage';

const navigateMock = vi.fn();
let scheduleData: unknown[] = [];
let programData: unknown = null;

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('@/hooks/useSchedule', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useSchedule')>('@/hooks/useSchedule');
  return { ...actual, useSchedule: () => ({ data: scheduleData, isLoading: false }) };
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const entry = {
  session_id: 9,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('SchedulePage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    scheduleData = [entry];
    programData = {
      program_id: 1,
      name: 'My Program',
      status: 'active',
      duration_weeks: 8,
      current_week: 1,
      start_date: '2026-07-27',
      weeks: {},
      advisories: [],
    };
  });

  it('shows the current week and its sessions', () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Week 1 of 8/)).toBeInTheDocument();
    expect(screen.getByText('Upper Body A')).toBeInTheDocument();
  });

  it('advances to the next week', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /next week/i }));

    expect(screen.getByText(/Week 2 of 8/)).toBeInTheDocument();
  });

  it('cannot go before week 1', () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /previous week/i })).toBeDisabled();
  });

  it('navigates to the session detail on select', async () => {
    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByText('Upper Body A'));

    expect(navigateMock).toHaveBeenCalledWith('/sessions/9');
  });

  it('explains an empty week for a program with no sessions', () => {
    scheduleData = [];

    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no sessions/i)).toBeInTheDocument();
  });

  it('links to program creation when there is no active program', () => {
    programData = null;

    render(
      <MemoryRouter>
        <SchedulePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /create program/i })).toBeInTheDocument();
  });
});
