import type { FeedbackAction, SlotPreview } from '@/types/program';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';
import { SlotExplanationPanel } from './SlotExplanationPanel';
import { formatSlotNote } from '@/utils/slotNote';

function formatEffortTarget(target: SlotPreview['effort_target']): string | null {
  if (!target) return null;
  if (target.method === 'percent_1rm') {
    return `${Math.round((target.pct ?? 0) * 100)}%`;
  }
  return `${target.method.toUpperCase()} ${target.value}`;
}

function formatRestSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder === 0 ? `${minutes}m` : `${minutes}m ${remainder}s`;
}

export function ExerciseSlotCard({
  slot,
  programId,
  onAction,
  onSwap,
  onPreview,
  readOnly = false,
}: {
  slot: SlotPreview;
  programId: number;
  onAction?: (a: FeedbackAction) => void;
  onSwap?: () => void;
  onPreview?: (exerciseId: number) => void;
  readOnly?: boolean;
}) {
  const effortLabel = formatEffortTarget(slot.effort_target);

  return (
    <div className="bg-white dark:bg-neutral-700/30 border border-neutral-200 dark:border-neutral-600 rounded-lg p-2">
      <div className="flex items-center gap-1">
        {slot.is_locked && (
          <span aria-label="locked" className="text-xs flex-shrink-0">
            🔒
          </span>
        )}
        {slot.is_user_swapped && (
          <span
            aria-label="swapped"
            className="text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0 rounded flex-shrink-0"
          >
            swapped
          </span>
        )}
      </div>

      <div className="mt-1">
        <div className="flex items-center justify-between gap-2">
          <h4
            onClick={() => onPreview?.(slot.exercise_id)}
            className={`font-semibold text-xs text-neutral-900 dark:text-neutral-50 leading-tight flex-1 min-w-0 ${
              onPreview
                ? 'cursor-pointer hover:text-teal-600 dark:hover:text-teal-400 transition-colors'
                : ''
            }`}
          >
            {slot.exercise_name}
          </h4>
          {!readOnly && onAction && onSwap && (
            <div className="flex-shrink-0">
              <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-1 mt-0.5">
          <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
            {slot.sets}×{slot.reps}
            {slot.load != null ? `@${slot.load}` : ''}
          </span>
          {effortLabel && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">{effortLabel}</span>
          )}
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            Rest: {formatRestSeconds(slot.rest_seconds)}
          </span>
          {slot.note && (
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
              {formatSlotNote(slot.note)}
            </span>
          )}
          {slot.rotation_pool.length > 1 && (
            <span className="text-xs text-teal-600 dark:text-teal-400 font-medium">🔁</span>
          )}
          {slot.tempo !== 'controlled' && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Tempo: {slot.tempo}
            </span>
          )}
        </div>

        {slot.warmup_sets.length > 0 && (
          <div className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
            Warm-up:{' '}
            {slot.warmup_sets.map((w) => `${Math.round(w.pct * 100)}%×${w.reps}`).join(', ')}
          </div>
        )}

        <SlotExplanationPanel programId={programId} workoutExerciseId={slot.workout_exercise_id} />
      </div>
    </div>
  );
}
