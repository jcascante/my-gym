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
}: {
  slot: SlotPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: () => void;
}) {
  const effortLabel = formatEffortTarget(slot.effort_target);
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <div className="flex items-center gap-2">
        {slot.is_locked && <span aria-label="locked">🔒</span>}
        {slot.is_user_swapped && (
          <span aria-label="swapped" className="text-xs text-blue-600">
            swapped
          </span>
        )}
        <span>{slot.exercise_name}</span>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-700">
        <span>
          {slot.sets} × {slot.reps}
          {slot.load != null ? ` @ ${slot.load}` : ''}
        </span>
        {effortLabel && <span className="text-xs text-neutral-500">{effortLabel}</span>}
        {slot.note && <span className="text-amber-600">{slot.note}</span>}
        <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
      </div>
    </div>
  );
}
