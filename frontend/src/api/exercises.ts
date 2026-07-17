import { apiClient } from '@/api/client';
import type { ExerciseResponse } from '@/types/exercise';

export async function listExercises(params?: {
  bodyRegion?: string;
  movementPattern?: string;
  muscleGroup?: string;
  equipmentTags?: string[];
  difficultyLevel?: string;
}): Promise<ExerciseResponse[]> {
  const queryParams = new URLSearchParams();

  if (params?.bodyRegion) queryParams.append('body_region', params.bodyRegion);
  if (params?.movementPattern) queryParams.append('movement_pattern', params.movementPattern);
  if (params?.muscleGroup) queryParams.append('muscle_group', params.muscleGroup);
  if (params?.difficultyLevel) queryParams.append('difficulty_level', params.difficultyLevel);

  if (params?.equipmentTags && params.equipmentTags.length > 0) {
    params.equipmentTags.forEach((tag) => queryParams.append('equipment_tags', tag));
  }

  const queryString = queryParams.toString();
  const url = queryString ? `/exercises?${queryString}` : '/exercises';

  const { data } = await apiClient.get<ExerciseResponse[]>(url);
  return data;
}

export async function getExercise(id: number): Promise<ExerciseResponse> {
  const { data } = await apiClient.get<ExerciseResponse>(`/exercises/${id}`);
  return data;
}
