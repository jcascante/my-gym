import { useQuery } from '@tanstack/react-query';
import { getSchedule, getUserStats } from '@/api/sessions';
import type { ScheduleEntry, UserStats } from '@/types/session';

export const sessionKeys = {
  schedule: (start: string, end: string) => ['schedule', start, end] as const,
  detail: (id: number) => ['session', id] as const,
};

export const statsKeys = {
  all: ['stats'] as const,
};

export function toIsoDate(d: Date): string {
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

export function weekRange(startDate: string, week: number): { start: string; end: string } {
  const [y, m, d] = startDate.split('-').map(Number);
  const start = new Date(y, m - 1, d + (week - 1) * 7);
  const end = new Date(y, m - 1, d + (week - 1) * 7 + 6);
  return { start: toIsoDate(start), end: toIsoDate(end) };
}

export function addDays(dateStr: string, delta: number): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  return toIsoDate(new Date(y, m - 1, d + delta));
}

export function programDateBounds(
  startDate: string,
  durationWeeks: number,
): { start: string; end: string } {
  return { start: startDate, end: weekRange(startDate, durationWeeks).end };
}

export function useSchedule(start: string, end: string) {
  return useQuery({
    queryKey: sessionKeys.schedule(start, end),
    queryFn: () => getSchedule(start, end),
  });
}

export function useTodaySession(): { session: ScheduleEntry | null; isLoading: boolean } {
  const today = toIsoDate(new Date());
  const { data, isLoading } = useSchedule(today, today);
  return { session: data?.[0] ?? null, isLoading };
}

export function useUserStats(): { stats: UserStats | undefined; isLoading: boolean } {
  const { data, isLoading } = useQuery({ queryKey: statsKeys.all, queryFn: getUserStats });
  return { stats: data, isLoading };
}

export function useWeeklyProgress(
  startDate: string | null | undefined,
  week: number | null | undefined,
): { completed: number; total: number; isLoading: boolean } {
  const range = startDate && week != null ? weekRange(startDate, week) : null;
  const { data, isLoading } = useQuery({
    queryKey: sessionKeys.schedule(range?.start ?? '', range?.end ?? ''),
    queryFn: () => getSchedule(range!.start, range!.end),
    enabled: range !== null,
  });
  const entries = data ?? [];
  return {
    completed: entries.filter((entry) => entry.status === 'completed').length,
    total: entries.length,
    isLoading,
  };
}
