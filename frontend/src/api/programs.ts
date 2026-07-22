import { apiClient } from '@/api/client';
import type {
  Alternative,
  DraftRequest,
  FeedbackAction,
  MatchRequest,
  ProgramPreview,
  TemplateMatchResponse,
} from '@/types/program';

export async function matchTemplates(
  req: MatchRequest,
  limit?: number,
  offset?: number,
): Promise<TemplateMatchResponse> {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const { data } = await apiClient.post<TemplateMatchResponse>('/programs/match', req, {
    params: { ...(limit !== undefined && { limit }), ...(offset !== undefined && { offset }) },
  });
  return data;
}

export async function createDraft(req: DraftRequest): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>('/programs/draft', req);
  return data;
}

export async function getProgramPreview(id: number): Promise<ProgramPreview> {
  const { data } = await apiClient.get<ProgramPreview>(`/programs/${id}/preview`);
  return data;
}

export async function submitFeedback(id: number, action: FeedbackAction): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>(`/programs/${id}/feedback`, action);
  return data;
}

export async function getSlotAlternatives(id: number, weId: number): Promise<Alternative[]> {
  const { data } = await apiClient.get<Alternative[]>(`/programs/${id}/slots/${weId}/alternatives`);
  return data;
}

export async function acceptProgram(id: number): Promise<ProgramPreview> {
  const { data } = await apiClient.post<ProgramPreview>(`/programs/${id}/accept`);
  return data;
}
