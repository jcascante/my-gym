import { useQuery } from '@tanstack/react-query';
import { getSession } from '@/api/sessions';
import { sessionKeys, useSchedule } from '@/hooks/useSchedule';
import type { SessionDetail } from '@/types/session';

export function useSession(sessionId: number | null) {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId ?? 0),
    queryFn: () => getSession(sessionId as number),
    enabled: sessionId !== null,
  });
}

export interface WorkoutForDate {
  session: SessionDetail | null;
  isRestDay: boolean;
  isLoading: boolean;
  error: unknown;
}

export function useWorkoutForDate(date: string): WorkoutForDate {
  const {
    data: entries,
    isLoading: scheduleLoading,
    error: scheduleError,
  } = useSchedule(date, date);
  const entrySessionId = entries?.[0]?.session_id ?? null;
  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSession(entrySessionId);

  return {
    session: session ?? null,
    isRestDay: !scheduleLoading && entrySessionId === null,
    isLoading: scheduleLoading || sessionLoading,
    error: scheduleError ?? sessionError ?? null,
  };
}
