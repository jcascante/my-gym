import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { logout, clearAuthToken } from '@/api/auth'
import { Button, Card } from '@/components'

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  const handleLogout = async () => {
    setLoggingOut(true)
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      clearAuthToken()
      clearAuth()
      navigate('/login')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-neutral-900 dark:to-neutral-800 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-2">Dashboard</h1>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">Welcome, {user?.first_name}! 👋</p>
          </div>
          <Button variant="secondary" onClick={handleLogout} isLoading={loggingOut}>
            Sign out
          </Button>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Workout Program Card */}
          <Card>
            <div className="mb-4">
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">Your Program</h2>
              <p className="text-neutral-600 dark:text-neutral-400">Personalized workout plan coming soon</p>
            </div>
            <div className="bg-neutral-100 dark:bg-neutral-700 rounded-lg p-6 text-center">
              <svg className="w-16 h-16 mx-auto text-neutral-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-neutral-600 dark:text-neutral-400">Your workout program will be displayed here</p>
            </div>
          </Card>

          {/* Tracking Card */}
          <Card>
            <div className="mb-4">
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">Track Workouts</h2>
              <p className="text-neutral-600 dark:text-neutral-400">Log your daily exercises and progress</p>
            </div>
            <div className="bg-neutral-100 dark:bg-neutral-700 rounded-lg p-6 text-center">
              <svg className="w-16 h-16 mx-auto text-neutral-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="text-neutral-600 dark:text-neutral-400">Start tracking your workouts today</p>
            </div>
          </Card>
        </div>

        {/* Stats Section */}
        <Card>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-6">Your Progress</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-primary-50 dark:bg-primary-900 rounded-lg p-6">
              <p className="text-sm font-medium text-primary-600 dark:text-primary-300 mb-2">Workouts Completed</p>
              <p className="text-3xl font-bold text-primary-900 dark:text-primary-100">0</p>
            </div>
            <div className="bg-success-50 dark:bg-success-900 rounded-lg p-6">
              <p className="text-sm font-medium text-success-600 dark:text-success-300 mb-2">Current Streak</p>
              <p className="text-3xl font-bold text-success-900 dark:text-success-100">0 days</p>
            </div>
            <div className="bg-warning-50 dark:bg-warning-900 rounded-lg p-6">
              <p className="text-sm font-medium text-warning-600 dark:text-warning-300 mb-2">This Week</p>
              <p className="text-3xl font-bold text-warning-900 dark:text-warning-100">0/4</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
