export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex gap-2 mb-6 text-sm">
      {steps.map((label, i) => (
        <li
          key={label}
          className={`px-3 py-2 rounded-lg font-medium transition-colors ${
            i === current
              ? 'bg-primary-600 dark:bg-primary-500 text-white'
              : i < current
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-neutral-400 dark:text-neutral-500'
          }`}
        >
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  );
}
