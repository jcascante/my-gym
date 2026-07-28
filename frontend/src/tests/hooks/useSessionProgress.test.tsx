import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import type { SlotPreview } from '@/types/program';

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
});
