import { apiClient } from '@/api/client';

export interface WorkoutReadinessPayload {
  readiness: number;
}

export async function postWorkoutReadiness(workoutId: number, readiness: number): Promise<void> {
  const payload: WorkoutReadinessPayload = {
    readiness,
  };

  await apiClient.patch(`/users/me/workouts/${workoutId}/readiness`, payload);
}
