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

// A correction is a second POST for the same set - the backend keeps both rows for
// audit but only the highest id is current. Dedupe defensively here too in case a
// stale cache ever returns both.
// Session-detail responses are already scoped to one session, so session_id is
// implicit here (unlike the backend's cross-session dedupe in get_set_logs_for_sessions).
function dedupeLoggedSets(loggedSets: LoggedSet[]): LoggedSet[] {
  const bestByKey = new Map<string, LoggedSet>();
  for (const log of loggedSets) {
    const key = `${log.workout_exercise_id}:${log.set_number}`;
    const current = bestByKey.get(key);
    if (!current || log.id > current.id) {
      bestByKey.set(key, log);
    }
  }
  return Array.from(bestByKey.values());
}

export function useSessionProgress(slots: SlotPreview[], loggedSets: LoggedSet[] = []) {
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);

  // Keyed on slot + logged-set content rather than either array's reference: callers
  // routinely pass freshly-built arrays each render, which would otherwise make this
  // effect "reset" every render. Serializing full slot content (not just
  // workout_exercise_id) matters because a reactive deload or an exercise swap can
  // change a slot's sets/load/exercise_id while keeping the same workout_exercise_id.
  const slotsKey = JSON.stringify({ slots, loggedSets });

  useEffect(() => {
    const deduped = dedupeLoggedSets(loggedSets);
    const seeded = slots.map((slot) => ({
      ...slot,
      completedSets: deduped
        .filter((log) => log.workout_exercise_id === slot.workout_exercise_id)
        .sort((a, b) => a.set_number - b.set_number)
        .map(toEntry),
    }));
    setExercises(seeded);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slotsKey]);

  const totalSets = exercises.reduce((sum, ex) => sum + ex.sets, 0);
  const completedSetsTotal = exercises.reduce((sum, ex) => sum + ex.completedSets.length, 0);
  const completedExercises = exercises.filter((ex) => ex.completedSets.length >= ex.sets).length;
  const progressPercentage = totalSets ? Math.min(100, (completedSetsTotal / totalSets) * 100) : 0;

  const recordSet = useCallback(
    (
      workoutExerciseId: number,
      setNumber: number,
      data: Omit<LoggedSetEntry, 'setNumber' | 'timestamp'>,
    ) => {
      setExercises((prev) =>
        prev.map((ex) =>
          ex.workout_exercise_id === workoutExerciseId
            ? {
                ...ex,
                completedSets: [
                  ...ex.completedSets.filter((s) => s.setNumber !== setNumber),
                  { ...data, setNumber, timestamp: new Date() },
                ].sort((a, b) => a.setNumber - b.setNumber),
              }
            : ex,
        ),
      );
    },
    [],
  );

  return {
    exercises,
    totalSets,
    completedSetsTotal,
    completedExercises,
    progressPercentage,
    recordSet,
  };
}
