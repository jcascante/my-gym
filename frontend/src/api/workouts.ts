import { apiClient } from '@/api/client';

export interface WorkoutReadinessPayload {
  readiness: number;
  phase?: 'pre' | 'post';
}

export async function postWorkoutReadiness(
  workoutId: number,
  readiness: number,
  phase?: 'pre' | 'post',
): Promise<void> {
  const payload: WorkoutReadinessPayload = {
    readiness,
    ...(phase && { phase }),
  };

  await apiClient.post(`/users/me/workouts/${workoutId}/readiness`, payload);
}
