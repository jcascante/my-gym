export interface ProgressBarProps {
  completed: number;
  total: number;
  label?: string;
  showPercentage?: boolean;
}

export function ProgressBar({
  completed,
  total,
  label = 'Progress',
  showPercentage = false,
}: ProgressBarProps) {
  const percentage = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="label-sm text-neutral-600 dark:text-neutral-400">{label}</p>
        {showPercentage && (
          <p className="label-sm text-neutral-600 dark:text-neutral-400">
            {Math.round(percentage)}%
          </p>
        )}
      </div>
      <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2 overflow-hidden">
        <div
          className="bg-success-600 h-full rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="text-body-sm text-neutral-600 dark:text-neutral-400 mt-2">
        {completed} of {total} {total === 1 ? 'workout' : 'workouts'} completed
      </p>
    </div>
  );
}
