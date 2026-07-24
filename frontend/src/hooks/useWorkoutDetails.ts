import { useQuery } from '@tanstack/react-query';
import { useProgramPreview } from './usePrograms';
import type { SlotPreview } from '@/types/program';

export interface WorkoutDetails {
  workout_id: number;
  name: string;
  slots: SlotPreview[];
  program_id: number;
}

/**
 * Fetch details for a specific workout.
 * Requires programId to be passed (retrieved from URL or program context).
 */
export function useWorkoutDetails(workoutId: number, programId: number | null) {
  // Only fetch program preview if we have a programId
  const {
    data: programPreview,
    isLoading: previewLoading,
    error: previewError,
  } = useProgramPreview(programId ? programId : null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['workout', workoutId, programId],
    enabled: !!programId && !!programPreview,
    queryFn: (): WorkoutDetails => {
      if (!programPreview) throw new Error('Program preview not loaded');

      // Find the workout in the program preview
      for (const week of Object.values(programPreview.weeks)) {
        const workout = Array.isArray(week) ? week.find((w) => w.workout_id === workoutId) : null;
        if (workout) {
          return {
            workout_id: workoutId,
            name: workout.name,
            slots: workout.slots,
            program_id: programId || 0,
          };
        }
      }

      throw new Error(`Workout ${workoutId} not found in program ${programId}`);
    },
  });

  return {
    data,
    isLoading: isLoading || previewLoading,
    error: error || previewError,
  };
}
