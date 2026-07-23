import { useEffect, useRef } from 'react';
import { Alert } from './Alert';
import { TemplateMatchCard } from './TemplateMatchCard';
import { Spinner } from './Spinner';
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
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !onLoadMore) return;

    const IOConstructor = (globalThis as Record<string, unknown>).IntersectionObserver as
      | (new (
          callback: IntersectionObserverCallback,
          options?: IntersectionObserverInit,
        ) => IntersectionObserver)
      | undefined;

    if (!IOConstructor) return;

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && !isLoading && hasMore) {
        onLoadMore();
      }
    };

    let observer: IntersectionObserver | { observe: (el: Element) => void; disconnect: () => void };

    try {
      observer = new IOConstructor(observerCallback, { rootMargin: '100px' });
    } catch {
      // Fallback for mocked IntersectionObserver that doesn't work with 'new' keyword
      const observerResult = (
        IOConstructor as unknown as (
          callback: IntersectionObserverCallback,
          options: IntersectionObserverInit,
        ) => IntersectionObserver | { observe: (el: Element) => void; disconnect: () => void }
      )(observerCallback, { rootMargin: '100px' });
      observer = observerResult;
    }

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [isLoading, hasMore, onLoadMore]);

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
      {!isLoading && !hasMore && matches.length > 0 && (
        <div className="text-center py-6">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            No more matches available
          </p>
        </div>
      )}
      <div
        ref={sentinelRef}
        className="h-1"
        data-testid="template-match-sentinel"
        aria-hidden="true"
        style={{ height: '1px' }}
      />
    </div>
  );
}
