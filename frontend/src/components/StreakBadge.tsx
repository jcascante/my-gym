export interface StreakBadgeProps {
  days: number;
  label?: string;
}

export function StreakBadge({ days, label = 'Day Streak' }: StreakBadgeProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 rounded-lg border-2 border-success-600 dark:border-success-500 bg-success-50 dark:bg-success-900/20">
      <div className="text-center">
        <p className="label-sm text-success-600 dark:text-success-400 mb-3">🔥</p>

        <div className="mb-4">
          <p className="text-5xl font-bold text-success-700 dark:text-success-300 font-variant-numeric tabular-nums">
            {days}
          </p>
        </div>

        <p className="body-md text-success-700 dark:text-success-300 font-medium">{label}</p>

        {days > 0 && (
          <p className="text-body-sm text-success-600 dark:text-success-400 mt-2">Keep it up! 💪</p>
        )}

        {days === 0 && (
          <p className="text-body-sm text-success-600 dark:text-success-400 mt-2">
            Start your streak today!
          </p>
        )}
      </div>
    </div>
  );
}
