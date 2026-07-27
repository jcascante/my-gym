import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '@/pages/DashboardPage';

const makeWorkout = (id: number, name: string) => ({
  workout_id: id,
  key: name.toLowerCase(),
  name,
  slots: [],
});

let programData: unknown;

const navigateMock = vi.fn();

vi.mock('@/hooks/usePrograms', () => ({
  useActiveProgram: () => ({ data: programData, isLoading: false }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      user: { id: 1, email: 'a@b.com', first_name: 'Jorge', last_name: 'C' },
      userProfile: { workout_duration_min: 45 },
    }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

describe('DashboardPage', () => {
  beforeEach(() => navigateMock.mockClear());

  it("shows the workout from the program's current week, not always week 1", () => {
    programData = {
      program_id: 1,
      name: 'My Program',
      status: 'active',
      duration_weeks: 3,
      current_week: 2,
      weeks: {
        '1': [makeWorkout(1, 'Week 1 Day A')],
        '2': [makeWorkout(2, 'Week 2 Day A')],
        '3': [makeWorkout(3, 'Week 3 Day A')],
      },
      advisories: [],
    };

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Week 2 Day A')).toBeInTheDocument();
    expect(screen.getByText('My Program • Week 2 • 0 exercises • 45 min')).toBeInTheDocument();
  });

  it('navigates to workout tracking when the card is clicked', async () => {
    programData = {
      program_id: 7,
      name: 'My Program',
      status: 'active',
      duration_weeks: 3,
      current_week: 2,
      weeks: {
        '2': [makeWorkout(2, 'Week 2 Day A')],
      },
      advisories: [],
    };

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /Start Week 2 Day A/ }));

    expect(navigateMock).toHaveBeenCalledWith('/workouts/2?programId=7');
  });
});
