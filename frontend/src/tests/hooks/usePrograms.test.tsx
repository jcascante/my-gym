import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useMatchTemplates,
  useCreateDraft,
  useProgramPreview,
  useSubmitFeedback,
  useSlotAlternatives,
  useAcceptProgram,
} from '@/hooks/usePrograms';
import * as api from '@/api/programs';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('usePrograms hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMatchTemplates', () => {
    it('returns matches on mutate', async () => {
      vi.spyOn(api, 'matchTemplates').mockResolvedValue([
        {
          template_id: 1,
          slug: 's',
          name: 'n',
          fit_pct: 90,
          factors: {},
          required_inputs: [],
        },
      ]);
      const { result } = renderHook(() => useMatchTemplates(), { wrapper });
      result.current.mutate({
        environment_id: 1,
        days_per_week: 3,
        session_duration_min: 60,
        fitness_focus: 'strength',
        weight_unit: 'kg',
        duration_weeks: 8,
      });
      await waitFor(() => expect(result.current.data?.[0].template_id).toBe(1));
    });
  });

  describe('useCreateDraft', () => {
    it('creates draft on mutate', async () => {
      const mockPreview = {
        program_id: 1,
        name: 'Test Program',
        status: 'draft' as const,
        duration_weeks: 8,
        weeks: {},
      };
      vi.spyOn(api, 'createDraft').mockResolvedValue(mockPreview);
      const { result } = renderHook(() => useCreateDraft(), { wrapper });
      result.current.mutate({
        environment_id: 1,
        days_per_week: 3,
        session_duration_min: 60,
        fitness_focus: 'strength',
        weight_unit: 'kg',
        duration_weeks: 8,
        template_id: 1,
        required_inputs: {},
        progression_style: 'consistent',
        effort_method: null,
      });
      await waitFor(() => expect(result.current.data?.program_id).toBe(1));
    });
  });

  describe('useProgramPreview', () => {
    it('fetches preview when id is provided', async () => {
      const mockPreview = {
        program_id: 1,
        name: 'Test Program',
        status: 'draft' as const,
        duration_weeks: 8,
        weeks: {},
      };
      vi.spyOn(api, 'getProgramPreview').mockResolvedValue(mockPreview);
      const { result } = renderHook(() => useProgramPreview(1), { wrapper });
      await waitFor(() => expect(result.current.data?.program_id).toBe(1));
    });

    it('does not fetch when id is null', async () => {
      const spy = vi.spyOn(api, 'getProgramPreview');
      const { result } = renderHook(() => useProgramPreview(null), { wrapper });
      await new Promise((r) => setTimeout(r, 100));
      expect(spy).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('useSubmitFeedback', () => {
    it('submits feedback on mutate', async () => {
      const mockPreview = {
        program_id: 1,
        name: 'Test Program',
        status: 'draft' as const,
        duration_weeks: 8,
        weeks: {},
      };
      vi.spyOn(api, 'submitFeedback').mockResolvedValue(mockPreview);
      const { result } = renderHook(() => useSubmitFeedback(1), { wrapper });
      result.current.mutate({ type: 'lock', workout_exercise_id: 1 });
      await waitFor(() => expect(result.current.data?.program_id).toBe(1));
    });
  });

  describe('useSlotAlternatives', () => {
    it('fetches alternatives when enabled and weId is provided', async () => {
      const mockAlternatives = [
        { id: 1, name: 'Exercise 1', slug: 'ex1' },
        { id: 2, name: 'Exercise 2', slug: 'ex2' },
      ];
      vi.spyOn(api, 'getSlotAlternatives').mockResolvedValue(mockAlternatives);
      const { result } = renderHook(() => useSlotAlternatives(1, 2, true), { wrapper });
      await waitFor(() => expect(result.current.data?.length).toBe(2));
    });

    it('does not fetch when enabled is false', async () => {
      const spy = vi.spyOn(api, 'getSlotAlternatives');
      const { result } = renderHook(() => useSlotAlternatives(1, 2, false), { wrapper });
      await new Promise((r) => setTimeout(r, 100));
      expect(spy).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('useAcceptProgram', () => {
    it('accepts program on mutate', async () => {
      const mockPreview = {
        program_id: 1,
        name: 'Test Program',
        status: 'active' as const,
        duration_weeks: 8,
        weeks: {},
      };
      vi.spyOn(api, 'acceptProgram').mockResolvedValue(mockPreview);
      const { result } = renderHook(() => useAcceptProgram(1), { wrapper });
      result.current.mutate();
      await waitFor(() => expect(result.current.data?.status).toBe('active'));
    });
  });
});
