import { useAuthStore } from '@/store/auth'

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <div style={{ maxWidth: '900px', margin: '50px auto', padding: '20px' }}>
      <h1>Dashboard</h1>
      <p>Welcome, {user?.first_name}!</p>
      <p>Your workout program and tracking interface will appear here.</p>
      {/* TODO: Implement dashboard with workout program and tracking */}
    </div>
  )
}
