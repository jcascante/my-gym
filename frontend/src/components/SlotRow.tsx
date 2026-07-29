import type { FeedbackAction, SlotPreview } from '@/types/program';
import type { WeightUnit } from '@/types/programCreation';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';
import { formatSlotNote } from '@/utils/slotNote';
import { formatEffortDisplay } from '@/utils/effortDisplay';

export function SlotRow({
  slot,
  weightUnit,
  onAction,
  onSwap,
  onPreview,
  readOnly = false,
}: {
  slot: SlotPreview;
  weightUnit: WeightUnit;
  onAction?: (a: FeedbackAction) => void;
  onSwap?: () => void;
  onPreview?: (exerciseId: number) => void;
  readOnly?: boolean;
}) {
  const effortDisplay = formatEffortDisplay(
    slot.sets,
    slot.reps,
    slot.load,
    weightUnit,
    slot.effort_target,
  );
  return (
    <div className="px-6 py-4 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {slot.is_locked && (
            <span aria-label="locked" className="text-lg">
              🔒
            </span>
          )}
          {slot.is_user_swapped && (
            <span
              aria-label="swapped"
              className="text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded"
            >
              swapped
            </span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4
            onClick={() => onPreview?.(slot.exercise_id)}
            className={`font-semibold text-neutral-900 dark:text-neutral-50 truncate ${
              onPreview
                ? 'cursor-pointer hover:text-teal-600 dark:hover:text-teal-400 transition-colors'
                : ''
            }`}
          >
            {slot.exercise_name}
          </h4>
          <div className="flex flex-wrap gap-2 mt-1">
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              {effortDisplay}
            </span>
            {slot.note && (
              <span className="text-sm text-amber-600 dark:text-amber-400 font-medium">
                {formatSlotNote(slot.note)}
              </span>
            )}
            {slot.rotation_pool.length > 1 && (
              <span className="text-sm text-teal-600 dark:text-teal-400 font-medium">
                🔁 rotates weekly
              </span>
            )}
          </div>
        </div>
      </div>
      {!readOnly && onAction && onSwap && (
        <div className="ml-4 flex-shrink-0">
          <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
        </div>
      )}
    </div>
  );
}
