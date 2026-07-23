import { apiClient } from '@/api/client';
import type { SlotExplanation, TemplateExplanation } from '@/types/explain';

export async function getTemplateExplanation(programId: number): Promise<TemplateExplanation> {
  const { data } = await apiClient.get<TemplateExplanation>(
    `/programs/${programId}/explain/template`,
  );
  return data;
}

export async function getSlotExplanation(
  programId: number,
  workoutExerciseId: number,
): Promise<SlotExplanation> {
  const { data } = await apiClient.get<SlotExplanation>(
    `/programs/${programId}/explain/slot/${workoutExerciseId}`,
  );
  return data;
}
