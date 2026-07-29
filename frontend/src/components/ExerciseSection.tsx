import React from 'react';
import type { EffortMethod, WeightUnit } from '../types/programCreation';
import { SetRow } from './SetRow';
import { formatSlotNote } from '../utils/slotNote';
import { formatEffortDisplay } from '../utils/effortDisplay';
import type { ExerciseProgress, LoggedSetEntry } from '../hooks/useSessionProgress';

interface ExerciseSectionProps {
  exercise: ExerciseProgress;
  effort_method: EffortMethod;
  weightUnit: WeightUnit;
  isOpen: boolean;
  onToggle: () => void;
  onLogSet: (
    setNumber: number,
    data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod },
  ) => Promise<void> | void;
}

export const ExerciseSection: React.FC<ExerciseSectionProps> = ({
  exercise,
  effort_method,
  weightUnit,
  isOpen,
  onToggle,
  onLogSet,
}) => {
  const completedCount = exercise.completedSets.length;
  const isComplete = completedCount >= exercise.sets;
  const findSet = (setNumber: number): LoggedSetEntry | undefined =>
    exercise.completedSets.find((s) => s.setNumber === setNumber);

  const effortDisplay = formatEffortDisplay(
    exercise.sets,
    exercise.reps,
    exercise.load,
    weightUnit,
    exercise.effort_target,
  );

  return (
    <div
      data-testid={`exercise-section-${exercise.workout_exercise_id}`}
      className="border border-neutral-200 dark:border-neutral-700 rounded-lg mb-3 bg-white dark:bg-neutral-800 overflow-hidden"
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="w-full flex items-center justify-between px-4 py-3 gap-3"
      >
        <span className="flex items-center gap-2 font-semibold text-neutral-900 dark:text-neutral-100">
          {isComplete && <span className="text-success-600 dark:text-success-400">✓</span>}
          {exercise.exercise_name}
        </span>
        <span className="flex-1 text-sm text-neutral-600 dark:text-neutral-400 text-center">
          {effortDisplay}
        </span>
        <span className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400 whitespace-nowrap">
          {completedCount}/{exercise.sets} sets
          <span>{isOpen ? '▴' : '▾'}</span>
        </span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400">
            <span>
              Target: {effortDisplay} · Rest {Math.floor(exercise.rest_seconds / 60)}:
              {String(exercise.rest_seconds % 60).padStart(2, '0')}
            </span>
          </div>

          {exercise.note && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {formatSlotNote(exercise.note)}
              {exercise.adjustment_reason ? ` — ${exercise.adjustment_reason}` : ''}
            </p>
          )}

          <div className="space-y-2">
            {Array.from({ length: exercise.sets }, (_, i) => i + 1).map((setNumber) => (
              <SetRow
                key={setNumber}
                setNumber={setNumber}
                effort_method={effort_method}
                weightUnit={weightUnit}
                loggedSet={findSet(setNumber)}
                idPrefix={exercise.workout_exercise_id}
                onLogSet={(data) => onLogSet(setNumber, data)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
