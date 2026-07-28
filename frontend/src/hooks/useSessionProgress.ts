import { useState, useEffect, useCallback } from 'react';
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';

export interface LoggedSetEntry {
  setNumber: number;
  weight?: number;
  reps?: number;
  effort?: number;
  effort_method?: EffortMethod;
  timestamp: Date;
}

export interface ExerciseProgress extends SlotPreview {
  completedSets: LoggedSetEntry[];
}

export function useSessionProgress(slots: SlotPreview[]) {
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Keyed on slot content rather than the `slots` array reference: callers (including
  // this hook's own test) routinely pass a freshly-built array each render, which would
  // otherwise make this effect "reset" on every render and loop forever. Serializing the
  // full content (not just workout_exercise_id) matters because a reactive deload or an
  // exercise swap can change a slot's sets/load/exercise_id while keeping the same
  // workout_exercise_id - progress should reset when the prescription actually changes,
  // not just when the id list does.
  const slotsKey = JSON.stringify(slots);

  useEffect(() => {
    setExercises(slots.map((slot) => ({ ...slot, completedSets: [] })));
    setCurrentIndex(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slotsKey]);

  const currentExercise = exercises[currentIndex] ?? null;
  const completedSetsCount = currentExercise?.completedSets.length ?? 0;
  const isExerciseComplete = currentExercise ? completedSetsCount >= currentExercise.sets : false;
  const completedExercises = exercises.filter((ex) => ex.completedSets.length >= ex.sets).length;
  const progressPercentage = exercises.length ? (completedExercises / exercises.length) * 100 : 0;
  const isLastExercise = currentIndex === exercises.length - 1;

  const recordSet = useCallback(
    (set: Omit<LoggedSetEntry, 'setNumber' | 'timestamp'>): boolean => {
      let didComplete = false;
      setExercises((prev) => {
        const next = prev.map((ex, i) =>
          i === currentIndex
            ? {
                ...ex,
                completedSets: [
                  ...ex.completedSets,
                  { ...set, setNumber: ex.completedSets.length + 1, timestamp: new Date() },
                ],
              }
            : ex,
        );
        didComplete = next[currentIndex].completedSets.length >= next[currentIndex].sets;
        return next;
      });
      return didComplete;
    },
    [currentIndex],
  );

  const goToNext = useCallback(() => {
    setCurrentIndex((i) => (i < exercises.length - 1 ? i + 1 : i));
  }, [exercises.length]);

  return {
    exercises,
    currentIndex,
    currentExercise,
    completedSetsCount,
    isExerciseComplete,
    completedExercises,
    progressPercentage,
    isLastExercise,
    recordSet,
    goToNext,
  };
}
