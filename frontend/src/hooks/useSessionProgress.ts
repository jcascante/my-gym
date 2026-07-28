import { useState, useEffect, useCallback } from 'react';
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';
import type { LoggedSet } from '@/types/session';

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

function toEntry(log: LoggedSet): LoggedSetEntry {
  return {
    setNumber: log.set_number,
    weight: log.actual_weight ?? undefined,
    reps: log.actual_reps ?? undefined,
    effort: log.actual_rpe ?? undefined,
    effort_method: log.effort_method as EffortMethod,
    timestamp: new Date(),
  };
}

export function useSessionProgress(slots: SlotPreview[], loggedSets: LoggedSet[] = []) {
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Keyed on slot + logged-set content rather than either array's reference: callers
  // (including this hook's own test) routinely pass freshly-built arrays each render,
  // which would otherwise make this effect "reset" on every render and loop forever.
  // Serializing full slot content (not just workout_exercise_id) matters because a
  // reactive deload or an exercise swap can change a slot's sets/load/exercise_id while
  // keeping the same workout_exercise_id - progress should reset when the prescription
  // actually changes, not just when the id list does. loggedSets is included so that a
  // session already carrying server-recorded sets (e.g. after a page reload) resumes
  // from that recorded progress instead of restarting at zero and re-logging duplicates.
  const slotsKey = JSON.stringify({ slots, loggedSets });

  useEffect(() => {
    const seeded = slots.map((slot) => ({
      ...slot,
      completedSets: loggedSets
        .filter((log) => log.workout_exercise_id === slot.workout_exercise_id)
        .sort((a, b) => a.set_number - b.set_number)
        .map(toEntry),
    }));
    setExercises(seeded);
    const firstIncomplete = seeded.findIndex((ex) => ex.completedSets.length < ex.sets);
    setCurrentIndex(firstIncomplete === -1 ? Math.max(seeded.length - 1, 0) : firstIncomplete);
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
