import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getSlotExplanation, getTemplateExplanation } from '@/api/explain';
import * as clientModule from '@/api/client';

vi.mock('@/api/client');

describe('explain api', () => {
  const mockGet = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (clientModule.apiClient as any).get = mockGet;
  });

  it('fetches the template explanation for a program', async () => {
    mockGet.mockResolvedValue({
      data: {
        template_id: 1,
        slug: 'full-body-x3',
        name: 'Full Body',
        fit_pct: 92,
        factors: { goal: 1.0 },
        tier: 'best',
        advisories: [],
      },
    });
    const res = await getTemplateExplanation(5);
    expect(mockGet).toHaveBeenCalledWith('/programs/5/explain/template');
    expect(res.slug).toBe('full-body-x3');
  });

  it('fetches the slot explanation for a workout exercise', async () => {
    mockGet.mockResolvedValue({
      data: {
        workout_exercise_id: 9,
        exercise_id: 3,
        exercise_name: 'Barbell Back Squat',
        factors: { variety: 1.0 },
        score: 0.8,
        ledger_contributions: [{ group: 'quads', effective_sets: 3.0 }],
        safety_note: null,
      },
    });
    const res = await getSlotExplanation(5, 9);
    expect(mockGet).toHaveBeenCalledWith('/programs/5/explain/slot/9');
    expect(res.workout_exercise_id).toBe(9);
  });
});
