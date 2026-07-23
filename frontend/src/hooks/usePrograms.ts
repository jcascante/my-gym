import { useState, useCallback, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  acceptProgram,
  createDraft,
  getProgramPreview,
  getSlotAlternatives,
  matchTemplates,
  submitFeedback,
} from '@/api/programs';
import type {
  DraftRequest,
  FeedbackAction,
  MatchRequest,
  ProgramPreview,
  TemplateMatch,
  TemplateMatchResponse,
} from '@/types/program';

export const programKeys = { preview: (id: number) => ['program', id] as const };

export interface InfiniteTemplateMatchesState {
  matches: TemplateMatch[];
  totalCount: number;
  isLoading: boolean;
  hasMore: boolean;
  fetchMore: () => Promise<void>;
}

export function useMatchTemplates() {
  return useMutation<TemplateMatchResponse, Error, MatchRequest>({
    mutationFn: (req: MatchRequest) => matchTemplates(req),
  });
}

export function useInfiniteTemplateMatches(req: MatchRequest): InfiniteTemplateMatchesState {
  const [matches, setMatches] = useState<TemplateMatch[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [currentOffset, setCurrentOffset] = useState(0);
  const [lastLimit, setLastLimit] = useState(4);

  const hasMore = currentOffset + lastLimit < totalCount;

  const fetchMore = useCallback(async () => {
    if (isLoading || !hasMore) {
      return;
    }

    setIsLoading(true);
    try {
      const nextOffset = currentOffset === 0 ? 4 : currentOffset + 3;
      const response = await matchTemplates(req, 3, nextOffset);

      setMatches((prev) => [...prev, ...response.matches]);
      setCurrentOffset(nextOffset);
      setLastLimit(response.limit);
      setTotalCount(response.total_count);
    } catch (error) {
      console.error('Error fetching more matches:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, hasMore, currentOffset, req]);

  useEffect(() => {
    const initialLoad = async () => {
      setIsLoading(true);
      try {
        const response = await matchTemplates(req, 4, 0);
        setMatches(response.matches);
        setTotalCount(response.total_count);
        setCurrentOffset(response.offset);
        setLastLimit(response.limit);
      } catch (error) {
        console.error('Error loading initial matches:', error);
        setMatches([]);
        setTotalCount(0);
      } finally {
        setIsLoading(false);
      }
    };

    void initialLoad();
  }, [req]);

  return {
    matches,
    totalCount,
    isLoading,
    hasMore,
    fetchMore,
  };
}

export function useCreateDraft() {
  return useMutation({ mutationFn: (req: DraftRequest) => createDraft(req) });
}

export function useProgramPreview(id: number | null, initialData?: ProgramPreview) {
  return useQuery({
    queryKey: id ? programKeys.preview(id) : ['program', 'none'],
    queryFn: () => getProgramPreview(id as number),
    enabled: id != null,
    initialData,
    // Seeded data is already fresh (just-created draft, or a feedback response written
    // via setQueryData) - without this, the default staleTime of 0 triggers an immediate
    // background refetch on every mount that just re-fetches what we already have.
    ...(initialData ? { staleTime: Infinity } : {}),
  });
}

export function useSubmitFeedback(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: FeedbackAction) => submitFeedback(id, action),
    onSuccess: (data) => qc.setQueryData(programKeys.preview(id), data),
  });
}

export function useSlotAlternatives(id: number, weId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['program', id, 'alternatives', weId],
    queryFn: () => getSlotAlternatives(id, weId as number),
    enabled: enabled && weId != null,
  });
}

export function useAcceptProgram(id: number) {
  return useMutation({ mutationFn: () => acceptProgram(id) });
}
