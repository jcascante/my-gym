import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import type { SlotPreview } from '@/types/program';
import type { LoggedSet } from '@/types/session';

const loggedSet = (
  id: number,
  workoutExerciseId: number,
  setNumber: number,
  weight: number,
  reps: number,
): LoggedSet => ({
  id,
  workout_exercise_id: workoutExerciseId,
  set_number: setNumber,
  actual_weight: weight,
  actual_reps: reps,
  actual_rpe: 8,
  effort_method: 'rpe',
});

const slot = (id: number, name: string, sets: number): SlotPreview => ({
  workout_exercise_id: id,
  exercise_id: id,
  exercise_name: name,
  sets,
  reps: 8,
  load: 80,
  rest_seconds: 120,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: '',
  warmup_sets: [],
});

describe('useSessionProgress', () => {
  it('returns every exercise up front, none logged', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2), slot(2, 'Row', 2)]),
    );

    expect(result.current.exercises.map((ex) => ex.exercise_name)).toEqual(['Bench', 'Row']);
    expect(result.current.totalSets).toBe(4);
    expect(result.current.completedSetsTotal).toBe(0);
    expect(result.current.progressPercentage).toBe(0);
  });

  it('logs a set out of order without touching other sets', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 3)]));

    act(() => {
      result.current.recordSet(1, 3, { weight: 90, reps: 6, effort: 9, effort_method: 'rpe' });
    });

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 3, weight: 90, reps: 6 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('marks an exercise complete once every set is logged, in any order', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 2)]));

    act(() => {
      result.current.recordSet(1, 2, { weight: 80, reps: 8, effort: 8, effort_method: 'rpe' });
    });
    expect(result.current.completedExercises).toBe(0);

    act(() => {
      result.current.recordSet(1, 1, { weight: 80, reps: 8, effort: 8, effort_method: 'rpe' });
    });
    expect(result.current.completedExercises).toBe(1);
    expect(result.current.progressPercentage).toBe(100);
  });

  it('overwrites a set when it is logged again (a correction)', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 1)]));

    act(() => {
      result.current.recordSet(1, 1, { weight: 80, reps: 8, effort: 7, effort_method: 'rpe' });
    });
    act(() => {
      result.current.recordSet(1, 1, { weight: 85, reps: 6, effort: 9, effort_method: 'rpe' });
    });

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 85, reps: 6, effort: 9 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('resumes already-logged sets from the server instead of starting at zero', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2)], [loggedSet(101, 1, 1, 80, 8)]),
    );

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 80, reps: 8 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });

  it('dedupes server-provided logs, keeping the highest id per set', () => {
    const { result } = renderHook(() =>
      useSessionProgress(
        [slot(1, 'Bench', 1)],
        [loggedSet(101, 1, 1, 80, 8), loggedSet(102, 1, 1, 85, 6)],
      ),
    );

    expect(result.current.exercises[0].completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 85, reps: 6 }),
    ]);
    expect(result.current.completedSetsTotal).toBe(1);
  });
});
