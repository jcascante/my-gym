import { useAuthStore } from '@/store/auth'

export default function OnboardingPage() {
  const user = useAuthStore((state) => state.user)
  const setUserProfile = useAuthStore((state) => state.setUserProfile)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement onboarding form submission
    setUserProfile({
      age: 25,
      gender: 'male',
      weight_kg: 70,
      height_cm: 180,
      activity_level: 'moderately_active',
      fitness_focus: 'strength',
      experience_level: 'beginner',
      days_per_week: 4,
      workout_duration_min: 60,
      equipment: 'gym',
      injuries_limitations: '',
      short_term_goals: 'Build strength',
      medium_term_goals: 'Gain muscle',
    })
  }

  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
      <h1>Welcome, {user?.first_name}!</h1>
      <p>Let's set up your fitness profile to create your personalized workout program.</p>
      <form onSubmit={handleSubmit}>
        {/* TODO: Add all onboarding form fields */}
        <button type="submit" style={{ padding: '10px 20px' }}>
          Complete Onboarding
        </button>
      </form>
    </div>
  )
}
