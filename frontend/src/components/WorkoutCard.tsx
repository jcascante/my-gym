import type { ScheduleEntry } from '@/types/session';
import { Card } from '@/components';

export interface WorkoutCardProps {
  entry: ScheduleEntry;
  programName: string;
  onSelect: () => void;
}

export function WorkoutCard({ entry, programName, onSelect }: WorkoutCardProps) {
  const exerciseLabel = `${entry.exercise_count} ${entry.exercise_count === 1 ? 'exercise' : 'exercises'}`;
  const meta = `${programName} • Week ${entry.week} • ${exerciseLabel} • ${entry.duration_min} min`;

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={`Start ${entry.workout_name}, ${programName} week ${entry.week}, ${exerciseLabel}, ${entry.duration_min} minutes`}
      className="block w-full text-left rounded-lg transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <Card padding="md" className="border-l-4 border-primary-600">
        <span className="flex items-center justify-between gap-4">
          <span className="block min-w-0">
            <span className="label-sm text-primary-700 dark:text-primary-400 tracking-wide block">
              Today
            </span>
            <span className="heading-lg text-neutral-900 dark:text-neutral-50 block truncate">
              {entry.workout_name}
            </span>
            <span className="body-sm text-neutral-600 dark:text-neutral-400 mt-1 block">
              {meta}
            </span>
          </span>
          <span
            aria-hidden="true"
            className="shrink-0 body-sm font-medium text-primary-700 dark:text-primary-400"
          >
            View →
          </span>
        </span>
      </Card>
    </button>
  );
}
