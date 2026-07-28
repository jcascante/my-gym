import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSchedule, useTodaySession, toIsoDate } from '@/hooks/useSchedule';
import { getSchedule } from '@/api/sessions';

vi.mock('@/api/sessions', () => ({ getSchedule: vi.fn() }));

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
