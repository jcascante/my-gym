import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import type { SlotPreview } from '@/types/program';
import type { LoggedSet } from '@/types/session';

const loggedSet = (
  workoutExerciseId: number,
  setNumber: number,
  weight: number,
  reps: number,
): LoggedSet => ({
  id: workoutExerciseId * 100 + setNumber,
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
  it('starts on the first exercise with nothing logged', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2), slot(2, 'Row', 2)]),
    );

    expect(result.current.currentExercise?.exercise_name).toBe('Bench');
    expect(result.current.completedSetsCount).toBe(0);
    expect(result.current.progressPercentage).toBe(0);
  });

  it('reports completion once the target set count is reached', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 2)]));

    act(() => {
      result.current.recordSet({ weight: 80, reps: 8 });
    });
    expect(result.current.isExerciseComplete).toBe(false);

    act(() => {
      result.current.recordSet({ weight: 80, reps: 8 });
    });
    expect(result.current.isExerciseComplete).toBe(true);
    expect(result.current.progressPercentage).toBe(100);
  });

  it('advances to the next exercise', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 1), slot(2, 'Row', 1)]),
    );

    act(() => {
      result.current.goToNext();
    });

    expect(result.current.currentExercise?.exercise_name).toBe('Row');
    expect(result.current.isLastExercise).toBe(true);
  });

  it('does not advance past the last exercise', () => {
    const { result } = renderHook(() => useSessionProgress([slot(1, 'Bench', 1)]));

    act(() => {
      result.current.goToNext();
    });

    expect(result.current.currentIndex).toBe(0);
  });

  it('resumes already-logged sets instead of restarting at zero', () => {
    const { result } = renderHook(() =>
      useSessionProgress([slot(1, 'Bench', 2)], [loggedSet(1, 1, 80, 8)]),
    );

    expect(result.current.completedSetsCount).toBe(1);
    expect(result.current.isExerciseComplete).toBe(false);

    act(() => {
      result.current.recordSet({ weight: 80, reps: 8 });
    });

    // The next logged set continues from set_number 2, not 1 again.
    expect(result.current.currentExercise?.completedSets).toEqual([
      expect.objectContaining({ setNumber: 1, weight: 80, reps: 8 }),
      expect.objectContaining({ setNumber: 2, weight: 80, reps: 8 }),
    ]);
    expect(result.current.isExerciseComplete).toBe(true);
  });

  it('resumes on the first incomplete exercise when an earlier one is already done', () => {
    const { result } = renderHook(() =>
      useSessionProgress(
        [slot(1, 'Bench', 1), slot(2, 'Row', 2)],
        [loggedSet(1, 1, 80, 8), loggedSet(2, 1, 60, 10)],
      ),
    );

    expect(result.current.currentExercise?.exercise_name).toBe('Row');
    expect(result.current.completedSetsCount).toBe(1);
  });

  it('lands on the last exercise when every set is already logged', () => {
    const { result } = renderHook(() =>
      useSessionProgress(
        [slot(1, 'Bench', 1), slot(2, 'Row', 1)],
        [loggedSet(1, 1, 80, 8), loggedSet(2, 1, 60, 10)],
      ),
    );

    expect(result.current.currentExercise?.exercise_name).toBe('Row');
    expect(result.current.isExerciseComplete).toBe(true);
    expect(result.current.progressPercentage).toBe(100);
  });
});
