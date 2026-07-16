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
      weeks: { '1': [{ workout_id: 1, key: 'a', name: 'Day A', slots: [] }] },
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
