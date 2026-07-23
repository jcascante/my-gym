import { apiClient } from '@/api/client';

export interface SetLogPayload {
  user_id?: number;
  workout_id: number;
  workout_exercise_id: number;
  set_number: number;
  actual_weight?: number;
  actual_reps?: number;
  actual_rpe?: number;
  effort_method?: string;
}

export async function logSetLog(
  workoutId: number,
  workoutExerciseId: number,
  setNumber: number,
  actualWeight?: number,
  actualReps?: number,
  actualRpe?: number,
  effortMethod: string = 'rpe',
): Promise<void> {
  const payload: SetLogPayload = {
    workout_id: workoutId,
    workout_exercise_id: workoutExerciseId,
    set_number: setNumber,
    actual_weight: actualWeight,
    actual_reps: actualReps,
    actual_rpe: actualRpe,
    effort_method: effortMethod,
  };

  await apiClient.post(`/users/me/workouts/${workoutId}/set-logs`, payload);
}
