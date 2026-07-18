import type { FeedbackAction, SlotPreview } from '@/types/program';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';

function formatEffortTarget(target: SlotPreview['effort_target']): string | null {
  if (!target) return null;
  if (target.method === 'percent_1rm') {
    return `${Math.round((target.pct ?? 0) * 100)}%`;
  }
  return `${target.method.toUpperCase()} ${target.value}`;
}

export function SlotRow({
  slot,
  onAction,
  onSwap,
  readOnly = false,
}: {
  slot: SlotPreview;
  onAction?: (a: FeedbackAction) => void;
  onSwap?: () => void;
  readOnly?: boolean;
}) {
  const effortLabel = formatEffortTarget(slot.effort_target);
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <div className="flex items-center gap-2">
        {slot.is_locked && <span aria-label="locked">🔒</span>}
        {slot.is_user_swapped && (
          <span
            aria-label="swapped"
            className="text-xs text-primary-600 dark:text-primary-400 font-medium"
          >
            swapped
          </span>
        )}
        <span className="text-neutral-900 dark:text-neutral-50">{slot.exercise_name}</span>
      </div>
      <div className="flex items-center gap-3 text-sm text-neutral-700 dark:text-neutral-300">
        <span>
          {slot.sets} × {slot.reps}
          {slot.load != null ? ` @ ${slot.load}` : ''}
        </span>
        {effortLabel && (
          <span className="text-xs text-neutral-500 dark:text-neutral-400">{effortLabel}</span>
        )}
        {slot.note && <span className="text-amber-600 dark:text-amber-400">{slot.note}</span>}
        {slot.rotation_pool.length > 1 && (
          <span className="text-xs text-primary-600 dark:text-primary-400 font-medium">
            🔁 rotates weekly
          </span>
        )}
        {!readOnly && onAction && onSwap && (
          <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
        )}
      </div>
    </div>
  );
}
