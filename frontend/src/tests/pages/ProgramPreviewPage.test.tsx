import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramPreviewPage from '@/pages/ProgramPreviewPage';

vi.mock('@/hooks/usePrograms', () => ({
  useProgramPreview: () => ({
    data: {
      program_id: 1,
      name: 'My Program',
      status: 'active',
      duration_weeks: 1,
      weeks: {
        '1': [
          {
            workout_id: 1,
            key: 'a',
            name: 'Day A',
            slots: [
              {
                workout_exercise_id: 1,
                exercise_id: 10,
                exercise_name: 'Bench Press',
                sets: 4,
                reps: 8,
                load: 185,
                rest_seconds: 180,
                note: null,
                is_locked: false,
                is_user_swapped: false,
                effort_target: { method: 'rpe', value: 8 },
                rotation_pool: [],
                tempo: 'controlled',
                warmup_sets: [],
              },
              {
                workout_exercise_id: 2,
                exercise_id: 11,
                exercise_name: 'Squats',
                sets: 3,
                reps: 5,
                load: 225,
                rest_seconds: 240,
                note: 'Go heavy',
                is_locked: true,
                is_user_swapped: false,
                effort_target: { method: 'percent_1rm', pct: 0.85 },
                rotation_pool: [],
                tempo: 'controlled',
                warmup_sets: [],
              },
            ],
          },
        ],
      },
      advisories: [],
    },
    isLoading: false,
  }),
}));

it('renders an accepted program read-only', () => {
  render(
    <MemoryRouter initialEntries={['/programs/1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/programs/:id" element={<ProgramPreviewPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  expect(screen.getByText('My Program')).toBeInTheDocument();
  expect(screen.getByText('Day A')).toBeInTheDocument();
});

it('displays exercise names and effort targets', () => {
  render(
    <MemoryRouter initialEntries={['/programs/1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/programs/:id" element={<ProgramPreviewPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  expect(screen.getByText('Bench Press')).toBeInTheDocument();
  expect(screen.getByText('Squats')).toBeInTheDocument();
  expect(screen.getByText('RPE 8')).toBeInTheDocument();
  expect(screen.getByText('85%')).toBeInTheDocument();
  expect(screen.getByText('Go heavy')).toBeInTheDocument();
});

it('displays lock icon for locked exercises', () => {
  render(
    <MemoryRouter initialEntries={['/programs/1']}>
      <QueryClientProvider client={new QueryClient()}>
        <Routes>
          <Route path="/programs/:id" element={<ProgramPreviewPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  const lockIcons = screen.getAllByLabelText('locked');
  expect(lockIcons).toHaveLength(1);
});
