import { useQuery } from '@tanstack/react-query';
import { listTrainingEnvironments } from '@/api/trainingEnvironments';

export const trainingEnvironmentKeys = { list: ['training-environments'] as const };

export function useTrainingEnvironments(options: { enabled: boolean }) {
  return useQuery({
    queryKey: trainingEnvironmentKeys.list,
    queryFn: listTrainingEnvironments,
    enabled: options.enabled,
  });
}
