import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCheckIns, useCreateCheckIn } from '@/hooks/useCheckIns';
import * as api from '@/api/checkins';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const checkIn = {
  id: 1,
  region: 'knee' as const,
  status: 'green' as const,
  note: null,
  created_at: '2026-01-01',
};

describe('useCheckIns hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCheckIns', () => {
    it('fetches the check-in history for a program', async () => {
      vi.spyOn(api, 'listCheckIns').mockResolvedValue([checkIn]);
      const { result } = renderHook(() => useCheckIns(5), { wrapper });
      await waitFor(() => expect(result.current.data?.[0].id).toBe(1));
      expect(api.listCheckIns).toHaveBeenCalledWith(5);
    });
  });

  describe('useCreateCheckIn', () => {
    it('creates a check-in for the program on mutate', async () => {
      vi.spyOn(api, 'createCheckIn').mockResolvedValue({
        check_in: checkIn,
        excluded: false,
        consult_recommended: false,
        draft_injury_record: null,
        advisories: [],
      });
      const { result } = renderHook(() => useCreateCheckIn(5), { wrapper });
      result.current.mutate({ region: 'knee', status: 'green' });
      await waitFor(() => expect(result.current.data?.check_in.id).toBe(1));
      expect(api.createCheckIn).toHaveBeenCalledWith(5, { region: 'knee', status: 'green' });
    });
  });
});
