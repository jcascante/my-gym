import type { SessionStatus } from '@/types/session';

export type DisplayStatus = 'done' | 'today' | 'upcoming' | 'missed' | 'in progress' | 'skipped';

// 'today' and 'upcoming' are not stored: both are scheduled rows, split by date.
export function displayStatus(
  status: SessionStatus,
  scheduledDate: string,
  today: string,
): DisplayStatus {
  if (status === 'completed') return 'done';
  if (status === 'missed') return 'missed';
  if (status === 'skipped') return 'skipped';
  if (status === 'in_progress') return 'in progress';
  return scheduledDate === today ? 'today' : 'upcoming';
}

const STYLES: Record<DisplayStatus, string> = {
  done: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200',
  today: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
  upcoming: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200',
  missed: 'bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200',
  'in progress': 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
  skipped: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200',
};

export interface SessionStatusBadgeProps {
  status: SessionStatus;
  scheduledDate: string;
  today: string;
}

export function SessionStatusBadge({ status, scheduledDate, today }: SessionStatusBadgeProps) {
  const display = displayStatus(status, scheduledDate, today);
  return (
    <span className={`label-sm px-2 py-1 rounded-full whitespace-nowrap ${STYLES[display]}`}>
      {display}
    </span>
  );
}
