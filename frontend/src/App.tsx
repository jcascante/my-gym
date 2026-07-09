import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import DashboardPage from '@/pages/DashboardPage'
import OnboardingPage from '@/pages/OnboardingPage'

export default function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const userProfile = useAuthStore((state) => state.userProfile)

  return (
    <Routes>
      {!isAuthenticated ? (
        <>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </>
      ) : (
        <>
          {!userProfile && <Route path="*" element={<OnboardingPage />} />}
          {userProfile && <Route path="*" element={<DashboardPage />} />}
        </>
      )}
    </Routes>
  )
}
