import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useSchedule,
  useTodaySession,
  useWeeklyProgress,
  useUserStats,
  toIsoDate,
  addDays,
  programDateBounds,
} from '@/hooks/useSchedule';
import { getSchedule, getUserStats } from '@/api/sessions';

vi.mock('@/api/sessions', () => ({ getSchedule: vi.fn(), getUserStats: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const entry = {
  session_id: 1,
  scheduled_date: '2026-07-27',
  week: 1,
  status: 'scheduled' as const,
  workout_id: 4,
  workout_name: 'Upper Body A',
  exercise_count: 5,
  duration_min: 45,
};

describe('useSchedule', () => {
  beforeEach(() => vi.clearAllMocks());

  it('formats a Date as an ISO day string', () => {
    expect(toIsoDate(new Date(2026, 6, 27))).toBe('2026-07-27');
  });

  it('fetches the given range', async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);

    const { result } = renderHook(() => useSchedule('2026-07-27', '2026-08-02'), { wrapper });

    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(getSchedule).toHaveBeenCalledWith('2026-07-27', '2026-08-02');
  });

  it('returns null when today has no session', async () => {
    vi.mocked(getSchedule).mockResolvedValue([]);

    const { result } = renderHook(() => useTodaySession(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.session).toBeNull();
  });

  it("returns today's session when one exists", async () => {
    vi.mocked(getSchedule).mockResolvedValue([entry]);

    const { result } = renderHook(() => useTodaySession(), { wrapper });

    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.session?.session_id).toBe(1);
  });
});

describe('useWeeklyProgress', () => {
  beforeEach(() => vi.clearAllMocks());

  it('counts completed sessions against the week total', async () => {
    vi.mocked(getSchedule).mockResolvedValue([
      { ...entry, session_id: 1, status: 'completed' },
      { ...entry, session_id: 2, status: 'scheduled' },
      { ...entry, session_id: 3, status: 'completed' },
    ]);

    const { result } = renderHook(() => useWeeklyProgress('2026-07-27', 1), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.completed).toBe(2);
    expect(result.current.total).toBe(3);
  });

  it('returns zero progress when nothing is scheduled that week', async () => {
    vi.mocked(getSchedule).mockResolvedValue([]);

    const { result } = renderHook(() => useWeeklyProgress('2026-07-27', 1), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.completed).toBe(0);
    expect(result.current.total).toBe(0);
  });
});

describe('useUserStats', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns the stats from the API', async () => {
    vi.mocked(getUserStats).mockResolvedValue({
      workouts_this_month: 5,
      current_streak_days: 3,
      personal_records: 2,
      total_volume: 12500,
      weight_unit: 'kg',
    });

    const { result } = renderHook(() => useUserStats(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.stats).toEqual({
      workouts_this_month: 5,
      current_streak_days: 3,
      personal_records: 2,
      total_volume: 12500,
      weight_unit: 'kg',
    });
  });
});

describe('addDays', () => {
  it('adds days forward, including across a month boundary', () => {
    expect(addDays('2026-07-31', 1)).toBe('2026-08-01');
  });

  it('subtracts days backward, including across a month boundary', () => {
    expect(addDays('2026-08-01', -1)).toBe('2026-07-31');
  });
});

describe('programDateBounds', () => {
  it('spans from the start date through the end of the final week', () => {
    expect(programDateBounds('2026-07-01', 2)).toEqual({ start: '2026-07-01', end: '2026-07-14' });
  });
});
