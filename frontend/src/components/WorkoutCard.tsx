import { WorkoutPreview } from '@/types/program';
import { Button } from '@/components';

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
    <div className="card card-elevated border-l-4 border-primary-600">
      <div className="mb-4">
        <div className="flex items-baseline gap-2 mb-1">
          <h2 className="heading-lg">{workout.name}</h2>
        </div>
        <p className="body-sm text-neutral-600 dark:text-neutral-400">
          {programName} • Week {weekNumber}
        </p>
      </div>

      <div className="flex gap-4 mb-6 text-body-sm text-neutral-600 dark:text-neutral-400">
        <div className="flex items-center gap-1">
          <span>📋</span>
          <span>
            {exerciseCount} {exerciseCount === 1 ? 'exercise' : 'exercises'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span>⏱️</span>
          <span>{durationMin} min</span>
        </div>
      </div>

      <div className="mb-6">
        <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-3">Exercises</p>
        <div className="space-y-2">
          {workout.slots.map((slot) => (
            <div
              key={slot.workout_exercise_id}
              className="flex justify-between items-center text-body-sm py-2"
            >
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {slot.exercise_name}
              </span>
              <span className="font-variant-numeric tabular-nums text-neutral-600 dark:text-neutral-400 text-xs">
                {slot.sets} × {slot.reps}
                {slot.load && ` | ${slot.load} lb`}
              </span>
            </div>
          ))}
        </div>
      </div>

      <Button className="w-full btn btn-success" onClick={onStartClick}>
        Start Workout
      </Button>
    </div>
  );
}
