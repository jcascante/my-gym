import type { ScheduleEntry } from '@/types/session';
import { SessionStatusBadge } from '@/components/SessionStatusBadge';

export interface ScheduleRowProps {
  entry: ScheduleEntry;
  today: string;
  onSelect: (scheduledDate: string) => void;
}

export function ScheduleRow({ entry, today, onSelect }: ScheduleRowProps) {
  const [y, m, d] = entry.scheduled_date.split('-').map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    day: 'numeric',
  });

  return (
    <button
      type="button"
      onClick={() => onSelect(entry.scheduled_date)}
      className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <span className="flex items-baseline gap-4 min-w-0">
        <span className="label-sm text-neutral-600 dark:text-neutral-400 w-16 shrink-0">
          {label}
        </span>
        <span className="body-md text-neutral-900 dark:text-neutral-50 truncate">
          {entry.workout_name}
        </span>
      </span>
      <SessionStatusBadge
        status={entry.status}
        scheduledDate={entry.scheduled_date}
        today={today}
      />
    </button>
  );
}
