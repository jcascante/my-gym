import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  listTrainingEnvironments,
  createTrainingEnvironment,
  updateTrainingEnvironment,
  deleteTrainingEnvironment,
} from '@/api/trainingEnvironments';

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

describe('Training Environments API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listTrainingEnvironments', () => {
    it('should fetch the list of training environments', async () => {
      const mockResponse = {
        data: [
          {
            id: 1,
            name: 'Home Gym',
            environment_type: 'home',
            equipment_tags: [],
            is_default: true,
          },
        ],
      };
      vi.mocked(mockAxiosInstance.get).mockResolvedValueOnce(mockResponse);

      const result = await listTrainingEnvironments();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/training-environments');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('createTrainingEnvironment', () => {
    it('should post the payload and return the created environment', async () => {
      const payload = {
        name: 'Home Gym',
        environment_type: 'home' as const,
        equipment_tags: ['dumbbells'],
        is_default: true,
      };
      const mockResponse = { data: { id: 1, ...payload } };
      vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce(mockResponse);

      const result = await createTrainingEnvironment(payload);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/training-environments', payload);
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('updateTrainingEnvironment', () => {
    it('should patch the environment by id', async () => {
      const mockResponse = {
        data: {
          id: 1,
          name: 'Updated Gym',
          environment_type: 'home',
          equipment_tags: [],
          is_default: false,
        },
      };
      vi.mocked(mockAxiosInstance.patch).mockResolvedValueOnce(mockResponse);

      const result = await updateTrainingEnvironment(1, { name: 'Updated Gym' });

      expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/training-environments/1', {
        name: 'Updated Gym',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('deleteTrainingEnvironment', () => {
    it('should delete the environment by id', async () => {
      vi.mocked(mockAxiosInstance.delete).mockResolvedValueOnce({ data: undefined });

      await deleteTrainingEnvironment(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/training-environments/1');
    });
  });
});
