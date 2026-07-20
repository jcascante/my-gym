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
  age?: number | null;
  gender?: string | null;
  weight_kg?: number | null;
  height_cm?: number | null;
  activity_level?: string | null;
  fitness_focus?: string | null;
  experience_level?: string | null;
  days_per_week?: number | null;
  workout_duration_min?: number | null;
  injuries_limitations?: string | null;
  short_term_goals?: string | null;
  medium_term_goals?: string | null;
  goal_weights?: Record<string, number> | null;
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
