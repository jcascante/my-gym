import { useState, useMemo } from 'react';
import { WeekTabs } from './WeekTabs';
import { SessionCard } from './SessionCard';
import { ExerciseAlternativesModal } from './ExerciseAlternativesModal';
import { ExercisePreviewModal } from './ExercisePreviewModal';
import { Alert } from './Alert';
import { useSubmitFeedback } from '@/hooks/usePrograms';
import { useExercises } from '@/hooks/useExercises';
import type { FeedbackAction, ProgramPreview } from '@/types/program';
import type { Exercise, ExerciseResponse } from '@/types/exercise';

function mapExerciseResponse(response: ExerciseResponse): Exercise {
  const muscleGroupMap: Record<string, string> = {
    upper_body: 'Upper Body',
    lower_body: 'Lower Body',
    core: 'Core',
    full_body: 'Full Body',
  };

  return {
    id: response.id,
    name: response.name,
    muscleGroup: muscleGroupMap[response.body_region] || response.body_region,
    equipment: response.equipment_tags.map((tag) => tag.replace(/_/g, ' ')),
    difficulty:
      response.difficulty_level.charAt(0).toUpperCase() + response.difficulty_level.slice(1),
    description: response.instructions,
    targetMuscles: [...response.primary_muscles, ...response.secondary_muscles].map((m) =>
      m
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' '),
    ),
    instructions: response.instructions,
    formCues: response.form_cues,
    safetyNotes: response.safety_notes,
  };
}

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
  const [previewExerciseId, setPreviewExerciseId] = useState<number | null>(null);
  const feedback = useSubmitFeedback(programId);
  const { data: allExercises = [] } = useExercises();
  const onAction = (a: FeedbackAction) => feedback.mutate(a);

  const previewExercise = useMemo(() => {
    if (!previewExerciseId) return null;
    const response = allExercises.find((ex) => ex.id === previewExerciseId);
    return response ? mapExerciseResponse(response) : null;
  }, [previewExerciseId, allExercises]);

  return (
    <>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-1">
            Review Your Program
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Review the generated program and make adjustments as needed
          </p>
        </div>
        {program.advisories.length > 0 && (
          <div className="space-y-2">
            {program.advisories.map((advisory, i) => (
              <Alert key={i} type={advisory.severity}>
                {advisory.message}
              </Alert>
            ))}
          </div>
        )}
        <WeekTabs weeks={weeks} active={active} onSelect={setActive} />
        <div className="space-y-4">
          {(program.weeks[String(active)] ?? []).map((w) => (
            <SessionCard
              key={w.workout_id}
              workout={w}
              onAction={onAction}
              onSwap={setSwapFor}
              onPreview={setPreviewExerciseId}
            />
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

      {previewExercise && (
        <ExercisePreviewModal
          exercise={previewExercise}
          onClose={() => setPreviewExerciseId(null)}
        />
      )}
    </>
  );
}
