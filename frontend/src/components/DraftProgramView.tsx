import { useState } from 'react';
import { WeekTabs } from './WeekTabs';
import { SessionCard } from './SessionCard';
import { ExerciseAlternativesModal } from './ExerciseAlternativesModal';
import { useSubmitFeedback } from '@/hooks/usePrograms';
import type { FeedbackAction, ProgramPreview } from '@/types/program';

export function DraftProgramView({
  program,
  programId,
}: {
  program: ProgramPreview;
  programId: number;
}) {
  const weeks = Object.keys(program.weeks)
    .map(Number)
    .sort((a, b) => a - b);
  const [active, setActive] = useState(weeks[0] ?? 1);
  const [swapFor, setSwapFor] = useState<number | null>(null);
  const feedback = useSubmitFeedback(programId);
  const onAction = (a: FeedbackAction) => feedback.mutate(a);
  return (
    <div>
      <WeekTabs weeks={weeks} active={active} onSelect={setActive} />
      <div className="space-y-4">
        {(program.weeks[String(active)] ?? []).map((w) => (
          <SessionCard key={w.workout_id} workout={w} onAction={onAction} onSwap={setSwapFor} />
        ))}
      </div>
      {swapFor != null && (
        <ExerciseAlternativesModal
          programId={programId}
          weId={swapFor}
          onPick={(exerciseId) => {
            onAction({ type: 'swap', workout_exercise_id: swapFor, exercise_id: exerciseId });
            setSwapFor(null);
          }}
          onClose={() => setSwapFor(null)}
        />
      )}
    </div>
  );
}
