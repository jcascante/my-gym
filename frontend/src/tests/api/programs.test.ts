import { describe, it, expect, vi, beforeEach } from 'vitest';
import { matchTemplates, submitFeedback } from '@/api/programs';
import * as clientModule from '@/api/client';

vi.mock('@/api/client');

describe('programs api', () => {
  const mockPost = vi.fn();
  const mockGet = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (clientModule.apiClient as any).post = mockPost;
    (clientModule.apiClient as any).get = mockGet;
  });

  it('posts match request', async () => {
    mockPost.mockResolvedValue({ data: [{ template_id: 1 }] });
    const res = await matchTemplates({
      environment_id: 1,
      days_per_week: 3,
      session_duration_min: 60,
      fitness_focus: 'strength',
      weight_unit: 'kg',
      duration_weeks: 8,
    });
    expect(mockPost).toHaveBeenCalledWith('/programs/match', expect.any(Object));
    expect(res[0].template_id).toBe(1);
  });

  it('posts feedback to program id', async () => {
    mockPost.mockResolvedValue({ data: { program_id: 5 } });
    await submitFeedback(5, { type: 'lock', workout_exercise_id: 9 });
    expect(mockPost).toHaveBeenCalledWith('/programs/5/feedback', {
      type: 'lock',
      workout_exercise_id: 9,
    });
  });
});
