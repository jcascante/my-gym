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

export async function getActiveProgram(): Promise<ProgramPreview | null> {
  try {
    const { data } = await apiClient.get<ProgramPreview>('/programs/active/current');
    return data;
  } catch (err: unknown) {
    if (isNotFoundError(err)) return null;
    throw err;
  }
}

function isNotFoundError(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'response' in err &&
    typeof (err as { response?: { status?: number } }).response?.status === 'number' &&
    (err as { response: { status: number } }).response.status === 404
  );
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
