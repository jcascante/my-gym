import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useWorkoutDetails } from '@/hooks/useWorkoutDetails';
import * as api from '@/api/programs';
import type { ProgramPreview, WorkoutPreview } from '@/types/program';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function makeWorkout(overrides: Partial<WorkoutPreview>): WorkoutPreview {
  return {
    workout_id: 1,
    key: 'day_a',
    name: 'Day A',
    slots: [],
    reactive_deload: false,
    deload_reason: null,
    ...overrides,
  };
}

// derive_week renders the same Workout row once per week, so the same workout_id
// appears in every week - only the current week carries live signals.
function makePreview(currentWeek: number | null): ProgramPreview {
  return {
    program_id: 1,
    name: 'Test Program',
    status: 'active',
    duration_weeks: 4,
    current_week: currentWeek,
    weeks: {
      1: [
        makeWorkout({
          slots: [
            {
              workout_exercise_id: 1,
              exercise_id: 1,
              exercise_name: 'Squat',
              sets: 3,
              reps: 5,
              load: 100,
              rest_seconds: 120,
              note: null,
              adjustment_reason: null,
              is_locked: false,
              is_user_swapped: false,
              effort_target: null,
              rotation_pool: [],
              tempo: '2020',
              warmup_sets: [],
            },
          ],
          reactive_deload: false,
          deload_reason: null,
        }),
      ],
      3: [
        makeWorkout({
          slots: [
            {
              workout_exercise_id: 1,
              exercise_id: 1,
              exercise_name: 'Squat',
              sets: 3,
              reps: 5,
              load: 90,
              rest_seconds: 120,
              note: null,
              adjustment_reason: 'high_rpe_recent_sessions',
              is_locked: false,
              is_user_swapped: false,
              effort_target: null,
              rotation_pool: [],
              tempo: '2020',
              warmup_sets: [],
            },
          ],
          reactive_deload: true,
          deload_reason: 'low_readiness_recent_sessions',
        }),
      ],
    },
    advisories: [],
  };
}

describe('useWorkoutDetails', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns the current week data, not week 1, when the same workout_id appears in both', async () => {
    vi.spyOn(api, 'getProgramPreview').mockResolvedValue(makePreview(3));

    const { result } = renderHook(() => useWorkoutDetails(1, 1), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.reactive_deload).toBe(true);
    expect(result.current.data?.deload_reason).toBe('low_readiness_recent_sessions');
    expect(result.current.data?.slots[0].adjustment_reason).toBe('high_rpe_recent_sessions');
  });

  it('falls back to scanning all weeks when current_week is null', async () => {
    vi.spyOn(api, 'getProgramPreview').mockResolvedValue(makePreview(null));

    const { result } = renderHook(() => useWorkoutDetails(1, 1), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    // No current week to prefer - falls back to the first match found (week 1, nominal).
    expect(result.current.data?.reactive_deload).toBe(false);
    expect(result.current.data?.slots[0].adjustment_reason).toBeNull();
  });
});
