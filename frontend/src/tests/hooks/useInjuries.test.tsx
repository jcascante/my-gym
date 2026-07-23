import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCreateInjuryRecord, useDeleteInjuryRecord, useInjuries } from '@/hooks/useInjuries';
import * as api from '@/api/injuries';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const injury = {
  id: 1,
  region: 'shoulder' as const,
  condition: 'tendinopathy' as const,
  phase: 'rehabilitating' as const,
  provocations: ['overhead' as const],
  severity: 2,
  reported_at: '2026-01-15',
  source: 'user_reported' as const,
};

describe('useInjuries hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useInjuries', () => {
    it('fetches the injury record list', async () => {
      vi.spyOn(api, 'listInjuryRecords').mockResolvedValue([injury]);
      const { result } = renderHook(() => useInjuries(), { wrapper });
      await waitFor(() => expect(result.current.data?.[0].id).toBe(1));
    });
  });

  describe('useCreateInjuryRecord', () => {
    it('creates an injury record on mutate', async () => {
      vi.spyOn(api, 'createInjuryRecord').mockResolvedValue(injury);
      const { result } = renderHook(() => useCreateInjuryRecord(), { wrapper });
      result.current.mutate({
        region: 'shoulder',
        condition: 'tendinopathy',
        phase: 'rehabilitating',
        provocations: ['overhead'],
        severity: 2,
        reported_at: '2026-01-15',
        source: 'user_reported',
      });
      await waitFor(() => expect(result.current.data?.id).toBe(1));
    });
  });

  describe('useDeleteInjuryRecord', () => {
    it('deletes an injury record on mutate', async () => {
      vi.spyOn(api, 'deleteInjuryRecord').mockResolvedValue(undefined);
      const { result } = renderHook(() => useDeleteInjuryRecord(), { wrapper });
      result.current.mutate(1);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.deleteInjuryRecord).toHaveBeenCalledWith(1);
    });
  });
});
