import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { saveUserProfile } from '@/api/auth'
import { Button, FormField, Card, Alert } from '@/components'

export default function OnboardingPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const setUserProfile = useAuthStore((state) => state.setUserProfile)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    age: '',
    gender: '',
    weight_kg: '',
    height_cm: '',
    activity_level: '',
    fitness_focus: '',
    experience_level: '',
    days_per_week: '',
    workout_duration_min: '',
    equipment: '',
    injuries_limitations: '',
    short_term_goals: '',
    medium_term_goals: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const profileData = {
        age: parseInt(formData.age) || undefined,
        gender: formData.gender || undefined,
        weight_kg: parseFloat(formData.weight_kg) || undefined,
        height_cm: parseInt(formData.height_cm) || undefined,
        activity_level: formData.activity_level || undefined,
        fitness_focus: formData.fitness_focus || undefined,
        experience_level: formData.experience_level || undefined,
        days_per_week: parseInt(formData.days_per_week) || undefined,
        workout_duration_min: parseInt(formData.workout_duration_min) || undefined,
        equipment: formData.equipment || undefined,
        injuries_limitations: formData.injuries_limitations || undefined,
        short_term_goals: formData.short_term_goals || undefined,
        medium_term_goals: formData.medium_term_goals || undefined,
      }

      const response = await saveUserProfile(profileData)
      setUserProfile(response.profile || undefined)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-neutral-900 dark:to-neutral-800 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <Card className="mb-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-2">
              Welcome, {user?.first_name}!
            </h1>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Let's set up your fitness profile to create your personalized workout program.
            </p>
          </div>

          {error && <Alert type="error" dismissible onDismiss={() => setError(null)} className="mb-6">{error}</Alert>}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Personal Info */}
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">Personal Information</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField
                  label="Age"
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  required
                  min="13"
                  max="120"
                />
                <div className="input-group">
                  <label htmlFor="gender" className="input-label">
                    Gender <span className="text-error-600">*</span>
                  </label>
                  <select
                    id="gender"
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <FormField
                  label="Weight (kg)"
                  type="number"
                  name="weight_kg"
                  value={formData.weight_kg}
                  onChange={handleChange}
                  required
                  min="20"
                  max="500"
                  step="0.1"
                />
                <FormField
                  label="Height (cm)"
                  type="number"
                  name="height_cm"
                  value={formData.height_cm}
                  onChange={handleChange}
                  required
                  min="100"
                  max="250"
                />
              </div>
            </div>

            {/* Fitness Level */}
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">Fitness Level</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="input-group">
                  <label htmlFor="experience" className="input-label">
                    Experience Level <span className="text-error-600">*</span>
                  </label>
                  <select
                    id="experience"
                    name="experience_level"
                    value={formData.experience_level}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select level</option>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
                <div className="input-group">
                  <label htmlFor="activity" className="input-label">
                    Activity Level <span className="text-error-600">*</span>
                  </label>
                  <select
                    id="activity"
                    name="activity_level"
                    value={formData.activity_level}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select level</option>
                    <option value="sedentary">Sedentary</option>
                    <option value="lightly_active">Lightly Active</option>
                    <option value="moderately_active">Moderately Active</option>
                    <option value="very_active">Very Active</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Workout Preferences */}
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">Workout Preferences</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="input-group">
                  <label htmlFor="focus" className="input-label">
                    Fitness Focus <span className="text-error-600">*</span>
                  </label>
                  <select
                    id="focus"
                    name="fitness_focus"
                    value={formData.fitness_focus}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select focus</option>
                    <option value="strength">Strength</option>
                    <option value="cardio">Cardio</option>
                    <option value="flexibility">Flexibility</option>
                    <option value="weight_loss">Weight Loss</option>
                    <option value="muscle_gain">Muscle Gain</option>
                  </select>
                </div>
                <FormField
                  label="Days per Week"
                  type="number"
                  name="days_per_week"
                  value={formData.days_per_week}
                  onChange={handleChange}
                  required
                  min="1"
                  max="7"
                />
                <FormField
                  label="Workout Duration (minutes)"
                  type="number"
                  name="workout_duration_min"
                  value={formData.workout_duration_min}
                  onChange={handleChange}
                  required
                  min="15"
                  max="300"
                  step="15"
                />
                <div className="input-group">
                  <label htmlFor="equipment" className="input-label">
                    Equipment Access <span className="text-error-600">*</span>
                  </label>
                  <select
                    id="equipment"
                    name="equipment"
                    value={formData.equipment}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select equipment</option>
                    <option value="home">Home (no equipment)</option>
                    <option value="dumbbells">Home (with dumbbells)</option>
                    <option value="gym">Gym</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Goals */}
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">Your Goals</h2>
              <div className="space-y-4">
                <FormField
                  label="Short-term Goals"
                  name="short_term_goals"
                  value={formData.short_term_goals}
                  onChange={handleChange}
                  placeholder="e.g., Build a consistent workout habit"
                />
                <FormField
                  label="Medium-term Goals"
                  name="medium_term_goals"
                  value={formData.medium_term_goals}
                  onChange={handleChange}
                  placeholder="e.g., Gain muscle and improve endurance"
                />
              </div>
            </div>

            {/* Additional Info */}
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">Additional Information</h2>
              <div className="input-group">
                <label htmlFor="injuries" className="input-label">
                  Injuries or Limitations
                </label>
                <textarea
                  id="injuries"
                  name="injuries_limitations"
                  value={formData.injuries_limitations}
                  onChange={handleChange}
                  placeholder="Let us know about any injuries or physical limitations..."
                  rows={3}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-md bg-white text-neutral-900 placeholder-neutral-400 transition-colors dark:bg-neutral-800 dark:border-neutral-600 dark:text-neutral-50 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900"
                />
              </div>
            </div>

            <Button type="submit" variant="primary" size="lg" isLoading={loading} className="w-full">
              Complete Onboarding
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}
