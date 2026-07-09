import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { logout, clearAuthToken } from '@/api/auth'

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const navigate = useNavigate()

  const handleLogout = async () => {
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
    <div style={{ maxWidth: '900px', margin: '50px auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Dashboard</h1>
        <button onClick={handleLogout} style={{ padding: '8px 16px', cursor: 'pointer' }}>
          Logout
        </button>
      </div>
      <p>Welcome, {user?.first_name}!</p>
      <p>Your workout program and tracking interface will appear here.</p>
      {/* TODO: Implement dashboard with workout program and tracking */}
    </div>
  )
}
