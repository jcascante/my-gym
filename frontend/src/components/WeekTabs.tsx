export function WeekTabs({
  weeks,
  active,
  onSelect,
}: {
  weeks: number[];
  active: number;
  onSelect: (w: number) => void;
}) {
  return (
    <div
      role="tablist"
      className="flex gap-1 overflow-x-auto border-b border-neutral-200 dark:border-neutral-700 mb-4"
    >
      {weeks.map((w) => (
        <button
          key={w}
          role="tab"
          aria-selected={w === active}
          onClick={() => onSelect(w)}
          className={`px-3 py-2 whitespace-nowrap transition-colors ${
            w === active
              ? 'border-b-2 border-primary-600 dark:border-primary-400 font-semibold text-neutral-900 dark:text-neutral-50'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'
          }`}
        >
          Week {w}
        </button>
      ))}
    </div>
  );
}
