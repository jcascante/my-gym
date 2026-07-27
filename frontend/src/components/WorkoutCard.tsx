import { WorkoutPreview } from '@/types/program';
import { Card } from '@/components';

export interface WorkoutCardProps {
  workout: WorkoutPreview;
  programName: string;
  weekNumber: number;
  durationMin?: number;
  onStartClick: () => void;
}

export function WorkoutCard({
  workout,
  programName,
  weekNumber,
  durationMin = 45,
  onStartClick,
}: WorkoutCardProps) {
  const exerciseCount = workout.slots.length;
  const exerciseLabel = `${exerciseCount} ${exerciseCount === 1 ? 'exercise' : 'exercises'}`;
  const meta = `${programName} • Week ${weekNumber} • ${exerciseLabel} • ${durationMin} min`;

  return (
    <button
      type="button"
      onClick={onStartClick}
      aria-label={`Start ${workout.name}, ${exerciseLabel}, ${durationMin} minutes`}
      className="block w-full text-left rounded-lg transition-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
    >
      <Card padding="md" className="border-l-4 border-primary-600">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="label-sm text-primary-700 dark:text-primary-400 uppercase tracking-wide">
              Today
            </p>
            <h2 className="heading-lg text-neutral-900 dark:text-neutral-50 truncate">
              {workout.name}
            </h2>
            <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1 truncate">{meta}</p>
          </div>
          <span
            aria-hidden="true"
            className="shrink-0 body-sm font-medium text-primary-700 dark:text-primary-400"
          >
            Start →
          </span>
        </div>
      </Card>
    </button>
  );
}
