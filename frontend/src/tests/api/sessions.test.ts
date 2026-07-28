import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getSchedule, getSession, logSessionSet, completeSession } from '@/api/sessions';
import * as clientModule from '@/api/client';

vi.mock('@/api/client');

describe('sessions api', () => {
  const mockGet = vi.fn();
  const mockPost = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (clientModule.apiClient as any).get = mockGet;
    (clientModule.apiClient as any).post = mockPost;
  });

  it('requests the schedule for a date range', async () => {
    mockGet.mockResolvedValue({ data: [] });

    await getSchedule('2026-07-27', '2026-08-02');

    expect(mockGet).toHaveBeenCalledWith('/users/me/schedule', {
      params: { start: '2026-07-27', end: '2026-08-02' },
    });
  });

  it('requests a single session by id', async () => {
    mockGet.mockResolvedValue({ data: { session_id: 5 } });

    const result = await getSession(5);

    expect(mockGet).toHaveBeenCalledWith('/users/me/sessions/5');
    expect(result.session_id).toBe(5);
  });

  it('posts a set log to the session, not the workout', async () => {
    mockPost.mockResolvedValue({ data: {} });

    await logSessionSet(5, { workout_exercise_id: 3, set_number: 1, actual_reps: 8 });

    expect(mockPost).toHaveBeenCalledWith('/users/me/sessions/5/set-logs', {
      workout_exercise_id: 3,
      set_number: 1,
      actual_reps: 8,
    });
  });

  it('completes a session', async () => {
    mockPost.mockResolvedValue({ data: { status: 'completed' } });

    const result = await completeSession(5);

    expect(mockPost).toHaveBeenCalledWith('/users/me/sessions/5/complete');
    expect(result.status).toBe('completed');
  });
});
