import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createInjuryRecord, deleteInjuryRecord, listInjuryRecords } from '@/api/injuries';

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

describe('Injuries API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listInjuryRecords', () => {
    it('should fetch the list of injury records', async () => {
      const mockResponse = {
        data: [
          {
            id: 1,
            region: 'shoulder',
            condition: 'tendinopathy',
            phase: 'rehabilitating',
            provocations: ['overhead'],
            severity: 2,
            reported_at: '2026-01-15',
            source: 'user_reported',
          },
        ],
      };
      vi.mocked(mockAxiosInstance.get).mockResolvedValueOnce(mockResponse);

      const result = await listInjuryRecords();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/me/injuries');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('createInjuryRecord', () => {
    it('should post the payload and return the created record', async () => {
      const payload = {
        region: 'shoulder' as const,
        condition: 'tendinopathy' as const,
        phase: 'rehabilitating' as const,
        provocations: ['overhead' as const],
        severity: 2,
        reported_at: '2026-01-15',
        source: 'user_reported' as const,
      };
      const mockResponse = { data: { id: 1, ...payload } };
      vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce(mockResponse);

      const result = await createInjuryRecord(payload);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/users/me/injuries', payload);
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('deleteInjuryRecord', () => {
    it('should delete the injury record by id', async () => {
      vi.mocked(mockAxiosInstance.delete).mockResolvedValueOnce({ data: undefined });

      await deleteInjuryRecord(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/users/me/injuries/1');
    });
  });
});
