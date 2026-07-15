import { apiClient } from '@/api/client';
import type { TrainingEnvironment, TrainingEnvironmentPayload } from '@/types/trainingEnvironment';

export async function listTrainingEnvironments(): Promise<TrainingEnvironment[]> {
  const response = await apiClient.get<TrainingEnvironment[]>('/training-environments');
  return response.data;
}

export async function createTrainingEnvironment(
  payload: TrainingEnvironmentPayload,
): Promise<TrainingEnvironment> {
  const response = await apiClient.post<TrainingEnvironment>('/training-environments', payload);
  return response.data;
}

export async function updateTrainingEnvironment(
  id: number,
  payload: Partial<TrainingEnvironmentPayload>,
): Promise<TrainingEnvironment> {
  const response = await apiClient.patch<TrainingEnvironment>(
    `/training-environments/${id}`,
    payload,
  );
  return response.data;
}

export async function deleteTrainingEnvironment(id: number): Promise<void> {
  await apiClient.delete(`/training-environments/${id}`);
}
