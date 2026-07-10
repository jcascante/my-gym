import { useAuthStore } from '@/store/auth';
import { Card } from '@/components';

export default function ProfilePage() {
  const user = useAuthStore((state) => state.user);
  const userProfile = useAuthStore((state) => state.userProfile);

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
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
            Fitness Profile
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {userProfile.age && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Age</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.age}
                </p>
              </div>
            )}
            {userProfile.gender && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Gender</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.gender}
                </p>
              </div>
            )}
            {userProfile.weight_kg && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Weight</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.weight_kg} kg
                </p>
              </div>
            )}
            {userProfile.height_cm && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Height</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.height_cm} cm
                </p>
              </div>
            )}
            {userProfile.experience_level && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Experience Level</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.experience_level}
                </p>
              </div>
            )}
            {userProfile.days_per_week && (
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Workout Days</p>
                <p className="text-lg font-medium text-neutral-900 dark:text-neutral-50">
                  {userProfile.days_per_week} days/week
                </p>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
