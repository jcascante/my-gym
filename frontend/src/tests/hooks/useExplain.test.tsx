import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSlotExplanation, useTemplateExplanation } from '@/hooks/useExplain';
import * as api from '@/api/explain';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useExplain hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useTemplateExplanation', () => {
    it('does not fetch when disabled', () => {
      const spy = vi.spyOn(api, 'getTemplateExplanation');
      renderHook(() => useTemplateExplanation(5, false), { wrapper });
      expect(spy).not.toHaveBeenCalled();
    });

    it('fetches the template explanation when enabled', async () => {
      vi.spyOn(api, 'getTemplateExplanation').mockResolvedValue({
        template_id: 1,
        slug: 'full-body-x3',
        name: 'Full Body',
        fit_pct: 92,
        factors: {},
        tier: 'best',
        advisories: [],
      });
      const { result } = renderHook(() => useTemplateExplanation(5, true), { wrapper });
      await waitFor(() => expect(result.current.data?.slug).toBe('full-body-x3'));
      expect(api.getTemplateExplanation).toHaveBeenCalledWith(5);
    });
  });

  describe('useSlotExplanation', () => {
    it('does not fetch when disabled', () => {
      const spy = vi.spyOn(api, 'getSlotExplanation');
      renderHook(() => useSlotExplanation(5, 9, false), { wrapper });
      expect(spy).not.toHaveBeenCalled();
    });

    it('fetches the slot explanation when enabled', async () => {
      vi.spyOn(api, 'getSlotExplanation').mockResolvedValue({
        workout_exercise_id: 9,
        exercise_id: 3,
        exercise_name: 'Barbell Back Squat',
        factors: {},
        score: 0.8,
        ledger_contributions: [],
        safety_note: null,
      });
      const { result } = renderHook(() => useSlotExplanation(5, 9, true), { wrapper });
      await waitFor(() => expect(result.current.data?.workout_exercise_id).toBe(9));
      expect(api.getSlotExplanation).toHaveBeenCalledWith(5, 9);
    });
  });
});
