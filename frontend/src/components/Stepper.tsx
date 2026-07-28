export function Stepper({
  steps,
  current,
  skipped = [],
}: {
  steps: string[];
  current: number;
  skipped?: number[];
}) {
  return (
    <ol className="flex gap-2 mb-6 text-sm">
      {steps.map((label, i) => {
        const isSkipped = skipped.includes(i);
        return (
          <li
            key={label}
            title={isSkipped ? `${label}: not needed for this template` : undefined}
            className={`px-3 py-2 rounded-lg font-medium transition-colors ${
              isSkipped
                ? 'border border-dashed border-neutral-300 dark:border-neutral-600 text-neutral-400 dark:text-neutral-500'
                : i === current
                  ? 'bg-primary-600 dark:bg-primary-500 text-white'
                  : i < current
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-neutral-400 dark:text-neutral-500'
            }`}
          >
            {isSkipped ? `${i + 1}. ${label} (skipped)` : `${i + 1}. ${label}`}
          </li>
        );
      })}
    </ol>
  );
}
