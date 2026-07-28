import { useState } from 'react';
import { Alert } from './Alert';
import { Spinner } from './Spinner';
import { useSlotExplanation } from '@/hooks/useExplain';

function factorLabel(key: string): string {
  return key.replace(/_/g, ' ');
}

export function SlotExplanationPanel({
  programId,
  workoutExerciseId,
}: {
  programId: number;
  workoutExerciseId: number;
}) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useSlotExplanation(programId, workoutExerciseId, open);

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-xs text-teal-600 dark:text-teal-400 hover:underline"
      >
        {open ? 'Hide why' : 'Why this exercise?'}
      </button>
      {open && (
        <div className="mt-1 p-2 rounded bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200 dark:border-neutral-700 text-xs space-y-1.5">
          {isLoading && <Spinner size="sm" />}
          {isError && (
            <p className="text-neutral-500 dark:text-neutral-400">
              Couldn&apos;t load an explanation for this slot.
            </p>
          )}
          {data && (
            <>
              <ul className="space-y-0.5">
                {Object.entries(data.factors).map(([key, value]) => (
                  <li key={key} className="flex items-center justify-between gap-2">
                    <span className="text-neutral-600 dark:text-neutral-400">
                      {factorLabel(key)}
                    </span>
                    <span className="font-medium text-neutral-900 dark:text-neutral-100">
                      {Math.round(value * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
              {data.ledger_contributions.length > 0 && (
                <div className="pt-1 border-t border-neutral-200 dark:border-neutral-700">
                  <p className="text-neutral-500 dark:text-neutral-400 mb-0.5">
                    Volume contribution
                  </p>
                  {data.ledger_contributions.map((contribution) => (
                    <div
                      key={contribution.group}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="text-neutral-600 dark:text-neutral-400">
                        {factorLabel(contribution.group)}
                      </span>
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">
                        {contribution.effective_sets.toFixed(1)} sets
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {data.safety_note && (
                <Alert type="info" className="mt-1">
                  {data.safety_note}
                </Alert>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
