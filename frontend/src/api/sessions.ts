import { apiClient } from '@/api/client';
import type { ScheduleEntry, SessionDetail, SessionSetLogPayload } from '@/types/session';

export async function getSchedule(start: string, end: string): Promise<ScheduleEntry[]> {
  const { data } = await apiClient.get<ScheduleEntry[]>('/users/me/schedule', {
    params: { start, end },
  });
  return data;
}

export async function getSession(sessionId: number): Promise<SessionDetail> {
  const { data } = await apiClient.get<SessionDetail>(`/users/me/sessions/${sessionId}`);
  return data;
}

export async function logSessionSet(
  sessionId: number,
  payload: SessionSetLogPayload,
): Promise<void> {
  await apiClient.post(`/users/me/sessions/${sessionId}/set-logs`, payload);
}

export async function postSessionReadiness(
  sessionId: number,
  readiness: number,
  phase?: 'pre' | 'post',
): Promise<void> {
  await apiClient.post(`/users/me/sessions/${sessionId}/readiness`, {
    readiness,
    ...(phase && { phase }),
  });
}

export async function completeSession(sessionId: number): Promise<SessionDetail> {
  const { data } = await apiClient.post<SessionDetail>(`/users/me/sessions/${sessionId}/complete`);
  return data;
}
