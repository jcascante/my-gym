import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/store/auth'

describe('Auth Store', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      userProfile: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  })

  describe('setAuth', () => {
    it('should set user, tokens, and authenticated state', () => {
      const user = {
        id: 1,
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
      }

      useAuthStore.getState().setAuth(user, 'access_token', 'refresh_token')

      const state = useAuthStore.getState()
      expect(state.user).toEqual(user)
      expect(state.accessToken).toBe('access_token')
      expect(state.refreshToken).toBe('refresh_token')
      expect(state.isAuthenticated).toBe(true)
      expect(state.userProfile).toBeNull()
    })

    it('should set user, tokens, and userProfile', () => {
      const user = {
        id: 1,
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
      }

      const profile = {
        id: 1,
        age: 30,
        gender: 'male',
        weight_kg: 75.5,
      }

      useAuthStore.getState().setAuth(user, 'access_token', 'refresh_token', profile)

      const state = useAuthStore.getState()
      expect(state.user).toEqual(user)
      expect(state.accessToken).toBe('access_token')
      expect(state.refreshToken).toBe('refresh_token')
      expect(state.userProfile).toEqual(profile)
      expect(state.isAuthenticated).toBe(true)
    })
  })

  describe('setUserProfile', () => {
    it('should set userProfile', () => {
      const profile = {
        id: 1,
        age: 28,
        gender: 'female',
        weight_kg: 65.0,
      }

      useAuthStore.getState().setUserProfile(profile)

      const state = useAuthStore.getState()
      expect(state.userProfile).toEqual(profile)
    })
  })

  describe('clearAuth', () => {
    it('should clear all auth state', () => {
      const user = {
        id: 1,
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
      }

      const profile = {
        id: 1,
        age: 30,
        gender: 'male',
      }

      useAuthStore.getState().setAuth(user, 'access_token', 'refresh_token', profile)

      useAuthStore.getState().clearAuth()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.userProfile).toBeNull()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('state persistence', () => {
    it('should persist state to localStorage', () => {
      const user = {
        id: 1,
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
      }

      useAuthStore.getState().setAuth(user, 'access_token', 'refresh_token')

      const stored = localStorage.getItem('auth-storage')
      expect(stored).toBeDefined()
      const parsed = JSON.parse(stored!)
      expect(parsed.state.user).toEqual(user)
    })
  })
})
