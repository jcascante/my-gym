import { Card } from './Card';
import type { TemplateMatch } from '@/types/program';

const TIER_LABELS: Record<TemplateMatch['tier'], string> = {
  best: 'Best match',
  strong: 'Strong fit',
  possible: 'Possible fit',
};

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
      className={`w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-neutral-950 rounded-lg transition-all ${
        selected
          ? 'ring-2 ring-primary-600 dark:ring-primary-500'
          : 'hover:shadow-md dark:hover:shadow-lg'
      }`}
    >
      <Card>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-neutral-900 dark:text-neutral-50">{match.name}</h3>
          <span className="text-primary-600 dark:text-primary-400 font-bold">
            {TIER_LABELS[match.tier]}
          </span>
        </div>
        <ul className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          {Object.entries(match.factors).map(([k, v]) => (
            <li key={k}>
              {k}: {Math.round(v * 100)}%
            </li>
          ))}
          <li className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
            Fit: {match.fit_pct}%
          </li>
        </ul>
      </Card>
    </button>
  );
}
