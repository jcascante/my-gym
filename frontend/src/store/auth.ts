import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  email: string
  first_name: string
  last_name: string
}

interface UserProfile {
  age?: number
  gender?: string
  weight_kg?: number
  height_cm?: number
  activity_level?: string
  fitness_focus?: string
  experience_level?: string
  days_per_week?: number
  workout_duration_min?: number
  equipment?: string
  injuries_limitations?: string
  short_term_goals?: string
  medium_term_goals?: string
}

interface AuthState {
  user: User | null
  userProfile: UserProfile | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  setUserProfile: (profile: UserProfile) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      userProfile: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) =>
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        }),
      setUserProfile: (profile) =>
        set({
          userProfile: profile,
        }),
      clearAuth: () =>
        set({
          user: null,
          userProfile: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
    },
  ),
)
