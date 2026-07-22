/* eslint-disable @typescript-eslint/no-unsafe-return */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInfiniteTemplateMatches } from '@/hooks/usePrograms';
import * as api from '@/api/programs';
import type { MatchRequest, TemplateMatch, TemplateMatchResponse } from '@/types/program';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function createMockMatch(id: number, name: string): TemplateMatch {
  return {
    template_id: id,
    slug: `template-${id}`,
    name,
    fit_pct: 85 + id,
    factors: { rest_quality: 0.8, equipment_access: 0.9 },
    required_inputs: [],
    tier: 'best',
    all_infeasible: false,
    advisories: [],
  };
}

const mockRequest: MatchRequest = {
  environment_id: 1,
  days_per_week: 3,
  session_duration_min: 60,
  fitness_focus: 'strength',
  weight_unit: 'kg',
  duration_weeks: 8,
};

const networkError: Error = new Error('Network error');

describe('useInfiniteTemplateMatches', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with empty matches and isLoading=true', () => {
    vi.spyOn(api, 'matchTemplates').mockResolvedValue({
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 10,
      offset: 0,
      limit: 4,
    });

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    expect(result.current.matches).toHaveLength(0);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.totalCount).toBe(0);
  });

  it('should load initial batch of 4 matches on mount', async () => {
    const mockResponse: TemplateMatchResponse = {
      matches: [
        createMockMatch(1, 'Match 1'),
        createMockMatch(2, 'Match 2'),
        createMockMatch(3, 'Match 3'),
        createMockMatch(4, 'Match 4'),
      ],
      total_count: 12,
      offset: 0,
      limit: 4,
    };

    vi.spyOn(api, 'matchTemplates').mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(4);
    expect(result.current.matches[0].template_id).toBe(1);
    expect(result.current.matches[3].template_id).toBe(4);
    expect(result.current.totalCount).toBe(12);
    expect(result.current.hasMore).toBe(true);
  });

  it('should fetch with correct limit=4 and offset=0 on initial mount', async () => {
    const matchSpy = vi.spyOn(api, 'matchTemplates').mockResolvedValueOnce({
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 10,
      offset: 0,
      limit: 4,
    });

    renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(matchSpy).toHaveBeenCalledWith(mockRequest, 4, 0);
    });
  });

  it('should append next batch without replacing existing matches', async () => {
    const firstBatch: TemplateMatchResponse = {
      matches: [
        createMockMatch(1, 'Match 1'),
        createMockMatch(2, 'Match 2'),
        createMockMatch(3, 'Match 3'),
        createMockMatch(4, 'Match 4'),
      ],
      total_count: 10,
      offset: 0,
      limit: 4,
    };

    const secondBatch: TemplateMatchResponse = {
      matches: [
        createMockMatch(5, 'Match 5'),
        createMockMatch(6, 'Match 6'),
        createMockMatch(7, 'Match 7'),
      ],
      total_count: 10,
      offset: 4,
      limit: 4,
    };

    const matchSpy = vi.spyOn(api, 'matchTemplates');
    matchSpy.mockResolvedValueOnce(firstBatch);
    matchSpy.mockResolvedValueOnce(secondBatch);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(4);

    await act(async () => {
      await result.current.fetchMore();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(7);
    expect(result.current.matches[0].template_id).toBe(1);
    expect(result.current.matches[4].template_id).toBe(5);
    expect(result.current.matches[6].template_id).toBe(7);
  });

  it('should calculate hasMore correctly based on offset and limit', async () => {
    const firstBatch: TemplateMatchResponse = {
      matches: [
        createMockMatch(1, 'Match 1'),
        createMockMatch(2, 'Match 2'),
        createMockMatch(3, 'Match 3'),
        createMockMatch(4, 'Match 4'),
      ],
      total_count: 10,
      offset: 0,
      limit: 4,
    };

    vi.spyOn(api, 'matchTemplates').mockResolvedValueOnce(firstBatch);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.hasMore).toBe(true);
  });

  it('should set hasMore=false when offset + limit >= totalCount', async () => {
    const lastBatch: TemplateMatchResponse = {
      matches: [createMockMatch(7, 'Match 7'), createMockMatch(8, 'Match 8')],
      total_count: 8,
      offset: 6,
      limit: 4,
    };

    vi.spyOn(api, 'matchTemplates').mockResolvedValueOnce(lastBatch);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.hasMore).toBe(false);
  });

  it('should not fetch more when hasMore=false', async () => {
    const lastBatch: TemplateMatchResponse = {
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 1,
      offset: 0,
      limit: 4,
    };

    const matchSpy = vi.spyOn(api, 'matchTemplates');
    matchSpy.mockResolvedValueOnce(lastBatch);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.hasMore).toBe(false);

    await act(async () => {
      await result.current.fetchMore();
    });

    expect(matchSpy).toHaveBeenCalledTimes(1);
  });

  it('should prevent simultaneous requests when isLoading=true', async () => {
    const firstBatch: TemplateMatchResponse = {
      matches: [
        createMockMatch(1, 'Match 1'),
        createMockMatch(2, 'Match 2'),
        createMockMatch(3, 'Match 3'),
        createMockMatch(4, 'Match 4'),
      ],
      total_count: 20,
      offset: 0,
      limit: 4,
    };

    const matchSpy = vi.spyOn(api, 'matchTemplates');
    let resolveFirstCall: () => void;
    const firstCallPromise = new Promise<void>((resolve) => {
      resolveFirstCall = resolve;
    });

    matchSpy.mockImplementationOnce(() => firstCallPromise.then(() => firstBatch));

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      await result.current.fetchMore();
    });

    expect(matchSpy).toHaveBeenCalledTimes(1);

    resolveFirstCall!();

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should handle fetch errors gracefully and retain existing matches', async () => {
    const firstBatch: TemplateMatchResponse = {
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 10,
      offset: 0,
      limit: 4,
    };

    const matchSpy = vi.spyOn(api, 'matchTemplates');
    matchSpy.mockResolvedValueOnce(firstBatch);
    matchSpy.mockRejectedValueOnce(networkError);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(1);

    await act(async () => {
      await result.current.fetchMore();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(1);
  });

  it('should allow retry after error by calling fetchMore again', async () => {
    const firstBatch: TemplateMatchResponse = {
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 8,
      offset: 0,
      limit: 4,
    };

    const secondBatch: TemplateMatchResponse = {
      matches: [
        createMockMatch(2, 'Match 2'),
        createMockMatch(3, 'Match 3'),
        createMockMatch(4, 'Match 4'),
      ],
      total_count: 8,
      offset: 4,
      limit: 4,
    };

    const matchSpy = vi.spyOn(api, 'matchTemplates');
    matchSpy.mockResolvedValueOnce(firstBatch);
    matchSpy.mockRejectedValueOnce(networkError);
    matchSpy.mockResolvedValueOnce(secondBatch);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(1);

    await act(async () => {
      await result.current.fetchMore();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(1);

    await act(async () => {
      await result.current.fetchMore();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.matches).toHaveLength(4);
    expect(result.current.matches[1].template_id).toBe(2);
  });

  it('should return correct totalCount from response', async () => {
    const mockResponse: TemplateMatchResponse = {
      matches: [createMockMatch(1, 'Match 1')],
      total_count: 42,
      offset: 0,
      limit: 4,
    };

    vi.spyOn(api, 'matchTemplates').mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useInfiniteTemplateMatches(mockRequest), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.totalCount).toBe(42);
  });
});
