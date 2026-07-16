import type { FeedbackAction, SlotPreview } from '@/types/program';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';

export function SlotRow({
  slot,
  onAction,
  onSwap,
}: {
  slot: SlotPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: () => void;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <div className="flex items-center gap-2">
        {slot.is_locked && <span aria-label="locked">🔒</span>}
        {slot.is_user_swapped && (
          <span aria-label="swapped" className="text-xs text-blue-600">
            swapped
          </span>
        )}
        <span>Exercise #{slot.exercise_id}</span>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-700">
        <span>
          {slot.sets} × {slot.reps}
          {slot.load != null ? ` @ ${slot.load}` : ''}
        </span>
        {slot.note && <span className="text-amber-600">{slot.note}</span>}
        <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
      </div>
    </div>
  );
}
