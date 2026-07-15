import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createProgram } from '@/api/programs';
import type { ProgramCreationPayload } from '@/types/programCreation';

const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  defaults: { headers: { common: {} } },
  interceptors: { response: { use: vi.fn() } },
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

const payload: ProgramCreationPayload = {
  environment_id: 1,
  days_per_week: 4,
  preferred_days: ['monday', 'wednesday', 'friday', 'saturday'],
  session_duration_min: 60,
  start_date: '2026-08-01',
  focus_areas: ['push', 'pull', 'legs'],
  weight_unit: 'kg',
  available_weight_increments: [1.25, 2.5, 5],
  progression_style: 'consistent',
};

describe('Programs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should post the full preferences payload', async () => {
    vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce({ data: undefined });

    await createProgram(payload);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/programs', payload);
  });

  it('should surface a 501 response to the caller', async () => {
    const error = {
      response: { status: 501, data: { detail: 'Program generation is not yet implemented.' } },
    };
    vi.mocked(mockAxiosInstance.post).mockRejectedValueOnce(error);

    await expect(createProgram(payload)).rejects.toBe(error);
  });
});
