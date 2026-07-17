export interface CompletedSet {
  setNumber: number;
  weight: number;
  reps: number;
  timestamp?: Date;
}

export interface CompletedSetsProps {
  sets: CompletedSet[];
  showTimestamps?: boolean;
}

export function CompletedSets({ sets, showTimestamps = false }: CompletedSetsProps) {
  if (sets.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="body-sm text-neutral-500 dark:text-neutral-400">
          No sets logged yet. Start by logging your first set above.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-3">Completed Sets</p>

      <div className="space-y-1">
        {sets.map((set) => (
          <div
            key={set.setNumber}
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700"
          >
            <div className="flex items-center gap-3 flex-1 font-variant-numeric tabular-nums">
              <span className="text-body-sm font-medium text-neutral-900 dark:text-neutral-100 min-w-10">
                Set {set.setNumber}
              </span>
              <span className="text-body-sm text-neutral-600 dark:text-neutral-400">
                {set.weight} lb
              </span>
              <span className="text-body-sm text-neutral-600 dark:text-neutral-400">
                {set.reps} reps
              </span>
            </div>

            <span className="text-success-600 dark:text-success-400 text-lg">✓</span>
          </div>
        ))}
      </div>

      {showTimestamps && sets.length > 0 && (
        <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
          <p className="label-sm text-neutral-600 dark:text-neutral-400">
            {sets.length} {sets.length === 1 ? 'set' : 'sets'} logged
          </p>
        </div>
      )}
    </div>
  );
}
