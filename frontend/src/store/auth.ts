import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserProfile {
  id?: number;
  age?: number;
  gender?: string;
  weight_kg?: number;
  height_cm?: number;
  activity_level?: string;
  fitness_focus?: string;
  experience_level?: string;
  days_per_week?: number;
  workout_duration_min?: number;
  equipment?: string;
  injuries_limitations?: string;
  short_term_goals?: string;
  medium_term_goals?: string;
}

interface AuthState {
  user: User | null;
  userProfile: UserProfile | null;
  isAuthenticated: boolean;
  // True until the initial /users/me check (driven by the httpOnly auth
  // cookie) resolves, so the router doesn't redirect to /login prematurely.
  isLoading: boolean;
  setAuth: (user: User, userProfile?: UserProfile | null) => void;
  setUserProfile: (profile: UserProfile) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      userProfile: null,
      isAuthenticated: false,
      isLoading: true,
      setAuth: (user, userProfile = null) =>
        set({
          user,
          userProfile: userProfile || null,
          isAuthenticated: true,
          isLoading: false,
        }),
      setUserProfile: (profile) =>
        set({
          userProfile: profile,
        }),
      clearAuth: () =>
        set({
          user: null,
          userProfile: null,
          isAuthenticated: false,
          isLoading: false,
        }),
      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      // Tokens live only in httpOnly cookies now; persisting isAuthenticated
      // would let stale UI state outlive an expired/cleared cookie.
      partialize: (state) => ({ user: state.user, userProfile: state.userProfile }),
    },
  ),
);
