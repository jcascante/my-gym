import { useQuery } from '@tanstack/react-query';
import { listExercises } from '@/api/exercises';
import type { ExerciseResponse } from '@/types/exercise';

export function useExercises(params?: {
  bodyRegion?: string;
  movementPattern?: string;
  muscleGroup?: string;
  equipmentTags?: string[];
  difficultyLevel?: string;
}) {
  return useQuery<ExerciseResponse[]>({
    queryKey: ['exercises', params],
    queryFn: () => listExercises(params),
  });
}
