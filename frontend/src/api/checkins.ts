import { apiClient } from '@/api/client';
import type { CheckIn, CheckInPayload, CheckInResult } from '@/types/checkin';

export async function createCheckIn(
  programId: number,
  payload: CheckInPayload,
): Promise<CheckInResult> {
  const { data } = await apiClient.post<CheckInResult>(`/programs/${programId}/check-ins`, payload);
  return data;
}

export async function listCheckIns(programId: number): Promise<CheckIn[]> {
  const { data } = await apiClient.get<CheckIn[]>(`/programs/${programId}/check-ins`);
  return data;
}
