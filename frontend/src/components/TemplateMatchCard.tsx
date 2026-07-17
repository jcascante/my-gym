import { Card } from './Card';
import type { TemplateMatch } from '@/types/program';

export function TemplateMatchCard({
  match,
  selected,
  onSelect,
}: {
  match: TemplateMatch;
  selected: boolean;
  onSelect: (m: TemplateMatch) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(match)}
      className={`w-full text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg ${selected ? 'ring-2 ring-blue-600' : ''}`}
    >
      <Card>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{match.name}</h3>
          <span className="text-blue-600 font-bold">{match.fit_pct}%</span>
        </div>
        <ul className="mt-2 text-sm text-gray-600">
          {Object.entries(match.factors).map(([k, v]) => (
            <li key={k}>
              {k}: {Math.round(v * 100)}%
            </li>
          ))}
        </ul>
      </Card>
    </button>
  );
}
