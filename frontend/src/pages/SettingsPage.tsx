import { Card } from '@/components'

export default function SettingsPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50 mb-8">Settings</h1>

      {/* Placeholder for future settings sections */}
      <Card padding="lg" className="mb-6">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
          Account Settings
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Settings coming soon. You'll be able to manage your account preferences, notifications, and more.
        </p>
      </Card>

      <Card padding="lg" className="mb-6">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
          Privacy & Security
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Manage your privacy settings and security options.
        </p>
      </Card>

      <Card padding="lg">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
          Notifications
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Control how you receive notifications from MyGym.
        </p>
      </Card>
    </div>
  )
}
