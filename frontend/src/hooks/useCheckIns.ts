import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createCheckIn, listCheckIns } from '@/api/checkins';
import type { CheckInPayload } from '@/types/checkin';

export const checkInKeys = {
  list: (programId: number) => ['program', programId, 'check-ins'] as const,
};

export function useCheckIns(programId: number) {
  return useQuery({
    queryKey: checkInKeys.list(programId),
    queryFn: () => listCheckIns(programId),
  });
}

export function useCreateCheckIn(programId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CheckInPayload) => createCheckIn(programId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: checkInKeys.list(programId) }),
  });
}
