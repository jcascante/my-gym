import { apiClient } from '@/api/client';
import type { InjuryRecord, InjuryRecordPayload } from '@/types/injury';

export async function listInjuryRecords(): Promise<InjuryRecord[]> {
  const response = await apiClient.get<InjuryRecord[]>('/users/me/injuries');
  return response.data;
}

export async function createInjuryRecord(payload: InjuryRecordPayload): Promise<InjuryRecord> {
  const response = await apiClient.post<InjuryRecord>('/users/me/injuries', payload);
  return response.data;
}

export async function deleteInjuryRecord(id: number): Promise<void> {
  await apiClient.delete(`/users/me/injuries/${id}`);
}
