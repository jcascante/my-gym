import { useState } from 'react';
import { Alert } from './Alert';
import { Card } from './Card';
import { Spinner } from './Spinner';
import { useTemplateExplanation } from '@/hooks/useExplain';

const TIER_LABELS: Record<'best' | 'strong' | 'possible', string> = {
  best: 'Best match',
  strong: 'Strong fit',
  possible: 'Possible fit',
};

export function TemplateExplanationPanel({ programId }: { programId: number }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useTemplateExplanation(programId, open);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-medium text-teal-600 dark:text-teal-400 hover:underline"
      >
        {open ? 'Hide why this template' : 'Why this template?'}
      </button>
      {open && (
        <Card padding="sm" className="mt-2">
          {isLoading && <Spinner size="sm" />}
          {isError && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Couldn&apos;t load an explanation for this template.
            </p>
          )}
          {data && (
            <div className="space-y-2 text-sm">
              <p className="font-semibold text-neutral-900 dark:text-neutral-50">
                {data.fit_pct}% fit &middot; {TIER_LABELS[data.tier]}
              </p>
              <ul className="space-y-0.5">
                {Object.entries(data.factors).map(([key, value]) => (
                  <li key={key} className="flex items-center justify-between gap-2">
                    <span className="text-neutral-600 dark:text-neutral-400">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-medium text-neutral-900 dark:text-neutral-100">
                      {Math.round(value * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
              {data.advisories.map((advisory, i) => (
                <Alert key={i} type={advisory.severity}>
                  {advisory.message}
                </Alert>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
