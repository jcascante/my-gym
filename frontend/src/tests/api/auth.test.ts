import { describe, it, expect, beforeEach, vi } from 'vitest';
import { signup, login, getCurrentUser, saveUserProfile } from '@/api/auth';

const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  defaults: { headers: { common: {} } },
  interceptors: { response: { use: vi.fn() } },
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('signup', () => {
    it('should call signup endpoint with correct payload', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
        },
      };

      vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce(mockResponse);

      const result = await signup({
        email: 'test@example.com',
        password: 'password123',
        first_name: 'John',
        last_name: 'Doe',
      });

      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('login', () => {
    it('should call login endpoint and return the logged-in user', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
        },
      };

      vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce(mockResponse);

      const result = await login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('getCurrentUser', () => {
    it('should fetch current user with profile', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          profile: {
            id: 1,
            age: 30,
            gender: 'male',
            weight_kg: 75.5,
          },
        },
      };

      vi.mocked(mockAxiosInstance.get).mockResolvedValueOnce(mockResponse);

      const result = await getCurrentUser();

      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch current user without profile', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          profile: null,
        },
      };

      vi.mocked(mockAxiosInstance.get).mockResolvedValueOnce(mockResponse);

      const result = await getCurrentUser();

      expect(result).toEqual(mockResponse.data);
      expect(result.profile).toBeNull();
    });
  });

  describe('saveUserProfile', () => {
    it('should save user profile and return updated user', async () => {
      const profileData = {
        age: 28,
        gender: 'female',
        weight_kg: 65.0,
      };

      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          profile: {
            id: 1,
            ...profileData,
          },
        },
      };

      vi.mocked(mockAxiosInstance.post).mockResolvedValueOnce(mockResponse);

      const result = await saveUserProfile(profileData);

      expect(result).toEqual(mockResponse.data);
      expect(result.profile).toBeDefined();
    });
  });
});
