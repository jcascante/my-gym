import { useQuery } from '@tanstack/react-query';
import { getSlotExplanation, getTemplateExplanation } from '@/api/explain';

export const explainKeys = {
  template: (programId: number) => ['program', programId, 'explain', 'template'] as const,
  slot: (programId: number, weId: number) =>
    ['program', programId, 'explain', 'slot', weId] as const,
};

export function useTemplateExplanation(programId: number, enabled: boolean) {
  return useQuery({
    queryKey: explainKeys.template(programId),
    queryFn: () => getTemplateExplanation(programId),
    enabled,
  });
}

export function useSlotExplanation(programId: number, workoutExerciseId: number, enabled: boolean) {
  return useQuery({
    queryKey: explainKeys.slot(programId, workoutExerciseId),
    queryFn: () => getSlotExplanation(programId, workoutExerciseId),
    enabled,
  });
}
