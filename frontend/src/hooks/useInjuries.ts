import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createInjuryRecord, deleteInjuryRecord, listInjuryRecords } from '@/api/injuries';
import type { InjuryRecordPayload } from '@/types/injury';

export const injuryKeys = { list: ['injuries'] as const };

export function useInjuries() {
  return useQuery({ queryKey: injuryKeys.list, queryFn: listInjuryRecords });
}

export function useCreateInjuryRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InjuryRecordPayload) => createInjuryRecord(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: injuryKeys.list }),
  });
}

export function useDeleteInjuryRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteInjuryRecord(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: injuryKeys.list }),
  });
}
