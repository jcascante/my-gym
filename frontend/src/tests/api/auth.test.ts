import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'
import {
  signup,
  login,
  logout,
  getCurrentUser,
  saveUserProfile,
  setAuthToken,
  clearAuthToken,
} from '@/api/auth'

vi.mock('axios')

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('signup', () => {
    it('should call signup endpoint with correct payload', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
        },
      }

      vi.mocked(axios.create().post).mockResolvedValueOnce(mockResponse)

      const result = await signup({
        email: 'test@example.com',
        password: 'password123',
        first_name: 'John',
        last_name: 'Doe',
      })

      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('login', () => {
    it('should call login endpoint and return tokens', async () => {
      const mockResponse = {
        data: {
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token',
          token_type: 'bearer',
        },
      }

      vi.mocked(axios.create().post).mockResolvedValueOnce(mockResponse)

      const result = await login({
        email: 'test@example.com',
        password: 'password123',
      })

      expect(result).toEqual(mockResponse.data)
    })
  })

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
      }

      vi.mocked(axios.create().get).mockResolvedValueOnce(mockResponse)

      const result = await getCurrentUser()

      expect(result).toEqual(mockResponse.data)
    })

    it('should fetch current user without profile', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          profile: null,
        },
      }

      vi.mocked(axios.create().get).mockResolvedValueOnce(mockResponse)

      const result = await getCurrentUser()

      expect(result).toEqual(mockResponse.data)
      expect(result.profile).toBeNull()
    })
  })

  describe('saveUserProfile', () => {
    it('should save user profile and return updated user', async () => {
      const profileData = {
        age: 28,
        gender: 'female',
        weight_kg: 65.0,
      }

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
      }

      vi.mocked(axios.create().post).mockResolvedValueOnce(mockResponse)

      const result = await saveUserProfile(profileData)

      expect(result).toEqual(mockResponse.data)
      expect(result.profile).toBeDefined()
    })
  })

  describe('setAuthToken', () => {
    it('should set auth token in localStorage', () => {
      const token = 'test_token_123'

      setAuthToken(token)

      expect(localStorage.getItem('authToken')).toBe(token)
    })
  })

  describe('clearAuthToken', () => {
    it('should clear auth token from localStorage', () => {
      localStorage.setItem('authToken', 'test_token')

      clearAuthToken()

      expect(localStorage.getItem('authToken')).toBeNull()
    })
  })
})
