import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useWorkoutForDate } from '@/hooks/useSession';
import { getSchedule, getSession } from '@/api/sessions';

vi.mock('@/api/sessions', () => ({ getSchedule: vi.fn(), getSession: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const entry = {
  session_id: 9,
  scheduled_date: '2026-08-05',
  week: 3,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body B',
  exercise_count: 5,
  duration_min: 45,
};

const detail = {
  ...entry,
  program_id: 1,
  program_name: 'My Program',
  weight_unit: 'kg' as const,
  slots: [],
  logged_sets: [],
  completed_at: null,
  reactive_deload: false,
  deload_reason: null,
};

describe('useWorkoutForDate', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns the full session detail for a training day', async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);
    vi.mocked(getSession).mockResolvedValue(detail);

    const { result } = renderHook(() => useWorkoutForDate('2026-08-05'), { wrapper });

    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.session?.session_id).toBe(9);
    expect(result.current.isRestDay).toBe(false);
    expect(getSession).toHaveBeenCalledWith(9);
  });

  it('reports a rest day and skips the session fetch when nothing is scheduled', async () => {
    vi.mocked(getSchedule).mockResolvedValue([]);

    const { result } = renderHook(() => useWorkoutForDate('2026-08-06'), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isRestDay).toBe(true);
    expect(result.current.session).toBeNull();
    expect(getSession).not.toHaveBeenCalled();
  });
});
