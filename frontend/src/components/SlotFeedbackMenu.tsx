import { useState } from 'react';
import type { FeedbackAction, SlotPreview } from '@/types/program';

export function SlotFeedbackMenu({
  slot,
  onAction,
  onSwap,
}: {
  slot: SlotPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: () => void;
}) {
  const [open, setOpen] = useState(false);
  const id = slot.workout_exercise_id;
  return (
    <div className="relative">
      <button
        type="button"
        aria-label="options"
        onClick={() => setOpen((o) => !o)}
        className="px-2"
      >
        ⋯
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-10 bg-white shadow rounded border text-sm">
          <button
            role="menuitem"
            className="block w-full px-3 py-2 text-left"
            onClick={() => {
              onSwap();
              setOpen(false);
            }}
          >
            Swap
          </button>
          <button
            role="menuitem"
            className="block w-full px-3 py-2 text-left"
            onClick={() => {
              onAction({ type: 'exclude', workout_exercise_id: id });
              setOpen(false);
            }}
          >
            Exclude
          </button>
          <button
            role="menuitem"
            className="block w-full px-3 py-2 text-left"
            onClick={() => {
              onAction({ type: 'regenerate', workout_exercise_id: id });
              setOpen(false);
            }}
          >
            Give me another
          </button>
          <button
            role="menuitem"
            className="block w-full px-3 py-2 text-left"
            onClick={() => {
              onAction({ type: 'lock', workout_exercise_id: id });
              setOpen(false);
            }}
          >
            {slot.is_locked ? 'Locked' : 'Lock'}
          </button>
        </div>
      )}
    </div>
  );
}
