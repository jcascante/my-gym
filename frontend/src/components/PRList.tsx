export interface PersonalRecord {
  id: number;
  exercise: string;
  weight: number;
  reps?: number;
  unit?: string;
  date: Date;
  isNew?: boolean;
}

export interface PRListProps {
  records: PersonalRecord[];
  showDates?: boolean;
}

export function PRList({ records, showDates = true }: PRListProps) {
  if (records.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-body-sm text-neutral-500 dark:text-neutral-400">
          No personal records yet. Start logging workouts to track your progress! 💪
        </p>
      </div>
    );
  }

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-2">
      {records.map((pr) => (
        <div
          key={pr.id}
          className="flex items-center justify-between p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-center gap-3 flex-1">
            <span className="text-2xl">🥇</span>
            <div>
              <p className="body-md font-semibold text-neutral-900 dark:text-neutral-100">
                {pr.exercise}
              </p>
              <div className="flex items-center gap-2">
                <p className="text-body-sm text-neutral-600 dark:text-neutral-400 font-variant-numeric tabular-nums">
                  {pr.weight} {pr.unit || 'lbs'}
                  {pr.reps && ` × ${pr.reps}`}
                </p>
                {pr.isNew && (
                  <span className="text-xs font-bold text-success-600 dark:text-success-400">
                    NEW
                  </span>
                )}
              </div>
            </div>
          </div>

          {showDates && (
            <p className="text-body-sm text-neutral-600 dark:text-neutral-400">
              {formatDate(pr.date)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
