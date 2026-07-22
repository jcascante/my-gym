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
  TemplateMatchResponse,
} from '@/types/program';

export const programKeys = { preview: (id: number) => ['program', id] as const };

export function useMatchTemplates() {
  return useMutation<TemplateMatchResponse, Error, MatchRequest>({
    mutationFn: (req: MatchRequest) => matchTemplates(req),
  });
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
