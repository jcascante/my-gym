import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import WorkoutTrackingPage from '@/pages/WorkoutTrackingPage';

vi.mock('@/store/auth');
vi.mock('@/hooks/useWorkoutDetails');
vi.mock('@/api/logging', () => ({ logSetLog: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@/api/workouts', () => ({ postWorkoutReadiness: vi.fn().mockResolvedValue(undefined) }));

import { useAuthStore } from '@/store/auth';
import { useWorkoutDetails } from '@/hooks/useWorkoutDetails';

const baseWorkoutDetails = {
  workout_id: 1,
  name: 'Day A',
  program_id: 1,
  reactive_deload: false,
  deload_reason: null,
  slots: [
    {
      workout_exercise_id: 1,
      exercise_id: 10,
      exercise_name: 'Bench Press',
      sets: 3,
      reps: 8,
      load: 100,
      rest_seconds: 120,
      note: null,
      adjustment_reason: null,
      is_locked: false,
      is_user_swapped: false,
      effort_target: null,
      rotation_pool: [],
      tempo: 'controlled',
      warmup_sets: [],
    },
  ],
};

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/workouts/1?programId=1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/workouts/:workoutId" element={<WorkoutTrackingPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(useAuthStore).mockReturnValue({ userProfile: { effort_method: 'rpe' } });
});

it('renders the reactive deload banner when the workout was deloaded', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      reactive_deload: true,
      deload_reason: 'Readiness has been low recently — built in a lighter week',
    },
    isLoading: false,
    error: null,
  });

  renderPage();

  expect(
    screen.getByText('Readiness has been low recently — built in a lighter week'),
  ).toBeInTheDocument();
});

it('does not render the banner when the workout was not deloaded', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: baseWorkoutDetails,
    isLoading: false,
    error: null,
  });

  renderPage();

  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('dismisses the deload banner on click and it stays dismissed', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      reactive_deload: true,
      deload_reason: 'Readiness has been low recently — built in a lighter week',
    },
    isLoading: false,
    error: null,
  });

  renderPage();

  fireEvent.click(screen.getByLabelText('Dismiss alert'));

  expect(
    screen.queryByText('Readiness has been low recently — built in a lighter week'),
  ).not.toBeInTheDocument();
});

it('shows a friendly label and the reason for an autoregulated exercise', () => {
  vi.mocked(useWorkoutDetails).mockReturnValue({
    data: {
      ...baseWorkoutDetails,
      slots: [
        {
          ...baseWorkoutDetails.slots[0],
          note: 'autoregulated',
          adjustment_reason: 'Recent sessions ran harder than planned — load reduced 5%',
        },
      ],
    },
    isLoading: false,
    error: null,
  });

  renderPage();

  expect(screen.getByText('Load adjusted')).toBeInTheDocument();
  expect(
    screen.getByText('Recent sessions ran harder than planned — load reduced 5%'),
  ).toBeInTheDocument();
});
