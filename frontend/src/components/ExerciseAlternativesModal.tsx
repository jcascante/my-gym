import { useSlotAlternatives } from '@/hooks/usePrograms';

export function ExerciseAlternativesModal({
  programId,
  weId,
  onPick,
  onClose,
}: {
  programId: number;
  weId: number;
  onPick: (exerciseId: number) => void;
  onClose: () => void;
}) {
  const { data, isLoading } = useSlotAlternatives(programId, weId, true);
  return (
    <div
      role="dialog"
      aria-label="Swap exercise"
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-20"
    >
      <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 w-80 max-h-[70vh] overflow-y-auto shadow-lg">
        <div className="flex justify-between mb-4">
          <h4 className="font-semibold text-neutral-900 dark:text-neutral-50">Swap exercise</h4>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-colors"
          >
            ✕
          </button>
        </div>
        {isLoading ? (
          <p className="text-neutral-600 dark:text-neutral-400">Loading…</p>
        ) : (
          (data ?? []).map((a) => (
            <button
              key={a.id}
              className="block w-full text-left px-3 py-2 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700/50 text-neutral-900 dark:text-neutral-50 transition-colors"
              onClick={() => onPick(a.id)}
            >
              {a.name}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
