import { WorkoutPreview } from '@/types/program';
import { Button, Card } from '@/components';

export interface WorkoutCardProps {
  workout: WorkoutPreview;
  programName: string;
  weekNumber: number;
  durationMin?: number;
  onStartClick?: () => void;
}

export function WorkoutCard({
  workout,
  programName,
  weekNumber,
  durationMin = 45,
  onStartClick,
}: WorkoutCardProps) {
  const exerciseCount = workout.slots.length;

  return (
    <Card padding="lg" className="border-l-4 border-primary-600">
      <div className="mb-4">
        <h2 className="heading-lg text-neutral-900 dark:text-neutral-50">{workout.name}</h2>
        <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1">
          {programName} • Week {weekNumber}
        </p>
      </div>

      <div className="flex items-center gap-5 mb-6 body-sm text-neutral-600 dark:text-neutral-400">
        <div className="flex items-center gap-1.5">
          <span className="text-base leading-none" aria-hidden="true">
            📋
          </span>
          <span>
            {exerciseCount} {exerciseCount === 1 ? 'exercise' : 'exercises'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-base leading-none" aria-hidden="true">
            ⏱️
          </span>
          <span>{durationMin} min</span>
        </div>
      </div>

      <div className="mb-6">
        <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-3">Exercises</p>
        <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {workout.slots.map((slot) => (
            <div
              key={slot.workout_exercise_id}
              className="flex items-center justify-between gap-4 body-sm py-3 first:pt-0 last:pb-0"
            >
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {slot.exercise_name}
              </span>
              <span className="shrink-0 font-variant-numeric tabular-nums text-neutral-600 dark:text-neutral-400 text-sm">
                {slot.sets} × {slot.reps}
                {slot.load ? ` @ ${slot.load} lb` : ''}
              </span>
            </div>
          ))}
        </div>
      </div>

      <Button variant="primary" size="lg" className="w-full" onClick={onStartClick}>
        Start Workout
      </Button>
    </Card>
  );
}
