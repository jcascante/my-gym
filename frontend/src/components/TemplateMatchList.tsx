import { Alert } from './Alert';
import { Spinner } from './Spinner';
import { TemplateMatchCard } from './TemplateMatchCard';
import type { TemplateMatch } from '@/types/program';

interface TemplateMatchListProps {
  matches: TemplateMatch[];
  selectedId: number | null;
  onSelect: (m: TemplateMatch) => void;
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export function TemplateMatchList({
  matches,
  selectedId,
  onSelect,
  isLoading = false,
  hasMore = false,
  onLoadMore,
}: TemplateMatchListProps) {
  if (matches.length === 0)
    return (
      <p className="text-neutral-500 dark:text-neutral-400 text-center py-8">
        No matching templates for your setup.
      </p>
    );

  return (
    <div className="space-y-3">
      {matches[0].all_infeasible && (
        <Alert type="warning" title="No perfect match found">
          None of your available templates fully match your setup. Here are the closest options.
        </Alert>
      )}
      {matches.map((m) => (
        <TemplateMatchCard
          key={m.template_id}
          match={m}
          selected={m.template_id === selectedId}
          onSelect={onSelect}
        />
      ))}
      {isLoading && (
        <div className="flex justify-center py-6" data-testid="loading-spinner">
          <Spinner size="md" />
        </div>
      )}
      {!isLoading && hasMore && (
        <div className="text-center py-6">
          <button
            type="button"
            onClick={onLoadMore}
            disabled={isLoading}
            data-testid="load-more-button"
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium tracking-widest uppercase text-neutral-600 dark:text-neutral-400 border border-neutral-300 dark:border-neutral-600 rounded-lg transition-colors hover:border-neutral-500 dark:hover:border-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-900/30 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
          >
            {isLoading ? (
              <svg
                className="inline mr-2 h-3 w-3 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : null}
            Load more
          </button>
        </div>
      )}
      {!isLoading && !hasMore && matches.length > 0 && (
        <div className="text-center py-6">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            No more matches available
          </p>
        </div>
      )}
    </div>
  );
}
