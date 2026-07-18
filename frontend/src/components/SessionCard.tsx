import { ExerciseSlotCard } from './ExerciseSlotCard';
import type { FeedbackAction, WorkoutPreview } from '@/types/program';

export function SessionCard({
  workout,
  onAction,
  onSwap,
  onPreview,
}: {
  workout: WorkoutPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: (weId: number) => void;
  onPreview?: (exerciseId: number) => void;
}) {
  return (
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      <div className="bg-gradient-to-r from-teal-50 to-blue-50 dark:from-teal-900/20 dark:to-blue-900/20 px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          {workout.name}
        </h3>
      </div>
      <div className="px-6 py-3 space-y-1.5">
        {workout.slots.map((s) => (
          <ExerciseSlotCard
            key={s.workout_exercise_id}
            slot={s}
            onAction={onAction}
            onSwap={() => onSwap(s.workout_exercise_id)}
            onPreview={onPreview}
          />
        ))}
      </div>
    </div>
  );
}
