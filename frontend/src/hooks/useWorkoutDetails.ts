import { useQuery } from '@tanstack/react-query';
import { useProgramPreview } from './usePrograms';
import type { SlotPreview } from '@/types/program';

export interface WorkoutDetails {
  workout_id: number;
  name: string;
  slots: SlotPreview[];
  program_id: number;
  reactive_deload: boolean;
  deload_reason: string | null;
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

      const toDetails = (
        workout: (typeof programPreview.weeks)[string][number],
      ): WorkoutDetails => ({
        workout_id: workoutId,
        name: workout.name,
        slots: workout.slots,
        program_id: programId || 0,
        reactive_deload: workout.reactive_deload,
        deload_reason: workout.deload_reason,
      });

      // The same workout_id appears in every week (derive_week renders one Workout row
      // per week), so we must look in the program's current active week first - otherwise
      // we'd always resolve to whichever week iterates first (week 1, nominal).
      if (programPreview.current_week != null) {
        const currentWeekWorkouts = programPreview.weeks[programPreview.current_week];
        const currentWeekMatch = Array.isArray(currentWeekWorkouts)
          ? currentWeekWorkouts.find((w) => w.workout_id === workoutId)
          : null;
        if (currentWeekMatch) return toDetails(currentWeekMatch);
      }

      // Fallback: DRAFT/ARCHIVED/future/overrun programs have no current_week, or the
      // workout wasn't found there - scan all weeks for a match.
      for (const week of Object.values(programPreview.weeks)) {
        const workout = Array.isArray(week) ? week.find((w) => w.workout_id === workoutId) : null;
        if (workout) return toDetails(workout);
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
