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
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b mb-4">
      {weeks.map((w) => (
        <button
          key={w}
          role="tab"
          aria-selected={w === active}
          onClick={() => onSelect(w)}
          className={`px-3 py-2 whitespace-nowrap ${w === active ? 'border-b-2 border-blue-600 font-semibold' : 'text-gray-500'}`}
        >
          Week {w}
        </button>
      ))}
    </div>
  );
}
