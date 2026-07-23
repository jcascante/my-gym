import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createCheckIn, listCheckIns } from '@/api/checkins';
import * as clientModule from '@/api/client';

vi.mock('@/api/client');

describe('checkins api', () => {
  const mockPost = vi.fn();
  const mockGet = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (clientModule.apiClient as any).post = mockPost;
    (clientModule.apiClient as any).get = mockGet;
  });

  it('posts a check-in to the program id', async () => {
    mockPost.mockResolvedValue({
      data: {
        check_in: { id: 1, region: 'knee', status: 'green', note: null, created_at: '2026-01-01' },
        excluded: false,
        consult_recommended: false,
        draft_injury_record: null,
        advisories: [],
      },
    });
    const res = await createCheckIn(5, { region: 'knee', status: 'green' });
    expect(mockPost).toHaveBeenCalledWith('/programs/5/check-ins', {
      region: 'knee',
      status: 'green',
    });
    expect(res.check_in.id).toBe(1);
  });

  it('lists check-ins for the program id', async () => {
    mockGet.mockResolvedValue({
      data: [{ id: 1, region: 'knee', status: 'green', note: null, created_at: '2026-01-01' }],
    });
    const res = await listCheckIns(5);
    expect(mockGet).toHaveBeenCalledWith('/programs/5/check-ins');
    expect(res).toHaveLength(1);
  });
});
