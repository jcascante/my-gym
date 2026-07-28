import { useQuery } from '@tanstack/react-query';
import { getSession } from '@/api/sessions';
import { sessionKeys } from '@/hooks/useSchedule';

export function useSession(sessionId: number | null) {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId ?? 0),
    queryFn: () => getSession(sessionId as number),
    enabled: sessionId !== null,
  });
}
