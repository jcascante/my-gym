import { useState } from 'react';
import { useAuthStore } from '@/store/auth';
import { saveUserProfile } from '@/api/auth';
import { getErrorMessage } from '@/api/errors';
import { Button, FormField, Card, Alert } from '@/components';
import type { UserProfile } from '@/store/auth';

export default function ProfilePage() {
  const user = useAuthStore((state) => state.user);
  const userProfile = useAuthStore((state) => state.userProfile);
  const setUserProfile = useAuthStore((state) => state.setUserProfile);

  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEditClick = () => {
    setFormData({
      age: userProfile?.age,
      gender: userProfile?.gender,
      weight_kg: userProfile?.weight_kg,
      height_cm: userProfile?.height_cm,
      activity_level: userProfile?.activity_level,
      fitness_focus: userProfile?.fitness_focus,
      experience_level: userProfile?.experience_level,
      days_per_week: userProfile?.days_per_week,
      workout_duration_min: userProfile?.workout_duration_min,
      injuries_limitations: userProfile?.injuries_limitations,
      short_term_goals: userProfile?.short_term_goals,
      medium_term_goals: userProfile?.medium_term_goals,
    });
    setError(null);
    setIsEditMode(true);
  };

  const handleCancel = () => {
    setIsEditMode(false);
    setFormData(null);
    setError(null);
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    if (!formData) return;
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData) return;

    setError(null);
    setLoading(true);

    try {
      const parseNumOrNull = (val: string | number | null | undefined): number | null => {
        if (val === '' || val === null || val === undefined) return null;
        const num = parseInt(val.toString());
        return Number.isNaN(num) ? null : num;
      };
      const parseFloatOrNull = (val: string | number | null | undefined): number | null => {
        if (val === '' || val === null || val === undefined) return null;
        const num = parseFloat(val.toString());
        return Number.isNaN(num) ? null : num;
      };
      const parseStringOrNull = (val: string | null | undefined): string | null => {
        const trimmed = val?.toString().trim();
        return trimmed && trimmed !== '' ? trimmed : null;
      };

      const profileData: UserProfile = {
        age: parseNumOrNull(formData.age),
        gender: parseStringOrNull(formData.gender),
        weight_kg: parseFloatOrNull(formData.weight_kg),
        height_cm: parseFloatOrNull(formData.height_cm),
        activity_level: parseStringOrNull(formData.activity_level),
        fitness_focus: parseStringOrNull(formData.fitness_focus),
        experience_level: parseStringOrNull(formData.experience_level),
        days_per_week: parseNumOrNull(formData.days_per_week),
        workout_duration_min: parseNumOrNull(formData.workout_duration_min),
        injuries_limitations: parseStringOrNull(formData.injuries_limitations),
        short_term_goals: parseStringOrNull(formData.short_term_goals),
        medium_term_goals: parseStringOrNull(formData.medium_term_goals),
      };

      const response = await saveUserProfile(profileData);
      if (!response.profile) {
        throw new Error('Failed to save profile');
      }
      setUserProfile(response.profile);
      setIsEditMode(false);
      setFormData(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50 mb-8">My Profile</h1>

      {/* Basic Info */}
      <Card padding="lg" className="mb-6">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
          Personal Information
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">First Name</p>
            <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
              {user?.first_name}
            </p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Last Name</p>
            <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
              {user?.last_name}
            </p>
          </div>
          <div className="sm:col-span-2">
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Email</p>
            <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
              {user?.email}
            </p>
          </div>
        </div>
      </Card>

      {/* Fitness Profile */}
      {userProfile && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50">
              Fitness Profile
            </h2>
            {!isEditMode && (
              <Button variant="secondary" size="sm" onClick={handleEditClick}>
                Edit Profile
              </Button>
            )}
          </div>

          {error && (
            <Alert type="error" dismissible onDismiss={() => setError(null)} className="mb-6">
              {error}
            </Alert>
          )}

          {!isEditMode ? (
            // Read-only view
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Personal Info Section */}
              <div className="sm:col-span-2">
                <h3 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                  Personal Information
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {userProfile.age && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">Age</p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.age}
                      </p>
                    </div>
                  )}
                  {userProfile.gender && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">Gender</p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.gender}
                      </p>
                    </div>
                  )}
                  {userProfile.weight_kg && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">Weight</p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.weight_kg} kg
                      </p>
                    </div>
                  )}
                  {userProfile.height_cm && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">Height</p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.height_cm} cm
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Fitness Level Section */}
              <div className="sm:col-span-2">
                <h3 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                  Fitness Level
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {userProfile.experience_level && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">
                        Experience Level
                      </p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.experience_level}
                      </p>
                    </div>
                  )}
                  {userProfile.activity_level && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">
                        Activity Level
                      </p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.activity_level}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Workout Preferences Section */}
              <div className="sm:col-span-2">
                <h3 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                  Workout Preferences
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {userProfile.fitness_focus && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">
                        Fitness Focus
                      </p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.fitness_focus}
                      </p>
                    </div>
                  )}
                  {userProfile.days_per_week && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">Workout Days</p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.days_per_week} days/week
                      </p>
                    </div>
                  )}
                  {userProfile.workout_duration_min && (
                    <div>
                      <p className="text-xs text-neutral-500 dark:text-neutral-500">
                        Workout Duration
                      </p>
                      <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                        {userProfile.workout_duration_min} minutes
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Goals Section */}
              {(userProfile.short_term_goals || userProfile.medium_term_goals) && (
                <div className="sm:col-span-2">
                  <h3 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                    Goals
                  </h3>
                  <div className="space-y-4">
                    {userProfile.short_term_goals && (
                      <div>
                        <p className="text-xs text-neutral-500 dark:text-neutral-500">
                          Short-term Goals
                        </p>
                        <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                          {userProfile.short_term_goals}
                        </p>
                      </div>
                    )}
                    {userProfile.medium_term_goals && (
                      <div>
                        <p className="text-xs text-neutral-500 dark:text-neutral-500">
                          Medium-term Goals
                        </p>
                        <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                          {userProfile.medium_term_goals}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Additional Info Section */}
              {userProfile.injuries_limitations && (
                <div className="sm:col-span-2">
                  <h3 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                    Additional Information
                  </h3>
                  <div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-500">
                      Injuries or Limitations
                    </p>
                    <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">
                      {userProfile.injuries_limitations}
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Edit mode
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Personal Info */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-4">
                  Personal Information
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FormField
                    label="Age"
                    type="number"
                    name="age"
                    value={formData?.age?.toString() || ''}
                    onChange={handleChange}
                    min="13"
                    max="120"
                  />
                  <div className="input-group">
                    <label htmlFor="gender" className="input-label">
                      Gender
                    </label>
                    <select
                      id="gender"
                      name="gender"
                      value={formData?.gender || ''}
                      onChange={handleChange}
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
                    value={formData?.weight_kg?.toString() || ''}
                    onChange={handleChange}
                    min="20"
                    max="500"
                    step="0.1"
                  />
                  <FormField
                    label="Height (cm)"
                    type="number"
                    name="height_cm"
                    value={formData?.height_cm?.toString() || ''}
                    onChange={handleChange}
                    min="100"
                    max="250"
                  />
                </div>
              </div>

              {/* Fitness Level */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-4">
                  Fitness Level
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="input-group">
                    <label htmlFor="experience" className="input-label">
                      Experience Level
                    </label>
                    <select
                      id="experience"
                      name="experience_level"
                      value={formData?.experience_level || ''}
                      onChange={handleChange}
                    >
                      <option value="">Select level</option>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label htmlFor="activity" className="input-label">
                      Activity Level
                    </label>
                    <select
                      id="activity"
                      name="activity_level"
                      value={formData?.activity_level || ''}
                      onChange={handleChange}
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
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-4">
                  Workout Preferences
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="input-group">
                    <label htmlFor="focus" className="input-label">
                      Fitness Focus
                    </label>
                    <select
                      id="focus"
                      name="fitness_focus"
                      value={formData?.fitness_focus || ''}
                      onChange={handleChange}
                    >
                      <option value="">Select focus</option>
                      <option value="strength">Strength</option>
                      <option value="endurance">Endurance</option>
                      <option value="flexibility">Flexibility</option>
                      <option value="weight_loss">Weight Loss</option>
                      <option value="muscle_gain">Muscle Gain</option>
                      <option value="general">General Fitness</option>
                    </select>
                  </div>
                  <FormField
                    label="Days per Week"
                    type="number"
                    name="days_per_week"
                    value={formData?.days_per_week?.toString() || ''}
                    onChange={handleChange}
                    min="1"
                    max="7"
                  />
                  <FormField
                    label="Workout Duration (minutes)"
                    type="number"
                    name="workout_duration_min"
                    value={formData?.workout_duration_min?.toString() || ''}
                    onChange={handleChange}
                    min="15"
                    max="300"
                    step="15"
                  />
                </div>
              </div>

              {/* Goals */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-4">
                  Your Goals
                </h3>
                <div className="space-y-4">
                  <FormField
                    label="Short-term Goals"
                    name="short_term_goals"
                    value={formData?.short_term_goals || ''}
                    onChange={handleChange}
                    placeholder="e.g., Build a consistent workout habit"
                  />
                  <FormField
                    label="Medium-term Goals"
                    name="medium_term_goals"
                    value={formData?.medium_term_goals || ''}
                    onChange={handleChange}
                    placeholder="e.g., Gain muscle and improve endurance"
                  />
                </div>
              </div>

              {/* Additional Info */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-4">
                  Additional Information
                </h3>
                <div className="input-group">
                  <label htmlFor="injuries" className="input-label">
                    Injuries or Limitations
                  </label>
                  <textarea
                    id="injuries"
                    name="injuries_limitations"
                    value={formData?.injuries_limitations || ''}
                    onChange={handleChange}
                    placeholder="Let us know about any injuries or physical limitations..."
                    rows={3}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-md bg-white text-neutral-900 placeholder-neutral-400 transition-colors dark:bg-neutral-800 dark:border-neutral-600 dark:text-neutral-50 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button type="submit" variant="primary" isLoading={loading} className="flex-1">
                  Save Changes
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCancel}
                  disabled={loading}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}
        </Card>
      )}
    </div>
  );
}
