import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { getCurrentUser } from '@/api/auth';
import { Layout, Spinner } from '@/components';
import { useDarkMode } from '@/hooks/useDarkMode';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import DashboardPage from '@/pages/DashboardPage';
import OnboardingPage from '@/pages/OnboardingPage';
import ProfilePage from '@/pages/ProfilePage';
import SettingsPage from '@/pages/SettingsPage';
import EnvironmentsPage from '@/pages/EnvironmentsPage';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';
import ProgramPreviewPage from '@/pages/ProgramPreviewPage';
import ProgramsListPage from '@/pages/ProgramsListPage';

export default function App() {
  useDarkMode();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const userProfile = useAuthStore((state) => state.userProfile);
  const setAuth = useAuthStore((state) => state.setAuth);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  useEffect(() => {
    // The httpOnly auth cookie (if any) is the source of truth for whether
    // the user is signed in — localStorage only caches user/profile for a
    // faster first paint, so re-derive isAuthenticated on every load.
    getCurrentUser()
      .then((userData) => setAuth(userData, userData.profile))
      .catch(() => clearAuth());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-dvh flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <Layout>
      <Routes>
        {!isAuthenticated ? (
          <>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="*" element={<Navigate to="/login" />} />
          </>
        ) : userProfile ? (
          <>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/environments" element={<EnvironmentsPage />} />
            <Route path="/programs" element={<ProgramsListPage />} />
            <Route path="/programs/new/:environmentId?" element={<ProgramBuilderPage />} />
            <Route path="/programs/:id" element={<ProgramPreviewPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </>
        ) : (
          <>
            <Route path="*" element={<OnboardingPage />} />
          </>
        )}
      </Routes>
    </Layout>
  );
}
