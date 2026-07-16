import { Card } from './Card';
import { SlotRow } from './SlotRow';
import type { FeedbackAction, WorkoutPreview } from '@/types/program';

export function SessionCard({
  workout,
  onAction,
  onSwap,
}: {
  workout: WorkoutPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: (weId: number) => void;
}) {
  return (
    <Card>
      <h3 className="font-semibold mb-2">{workout.name}</h3>
      {workout.slots.map((s) => (
        <SlotRow
          key={s.workout_exercise_id}
          slot={s}
          onAction={onAction}
          onSwap={() => onSwap(s.workout_exercise_id)}
        />
      ))}
    </Card>
  );
}
