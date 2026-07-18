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
      <div className="bg-white dark:bg-neutral-800 rounded-lg w-96 max-h-[70vh] overflow-hidden shadow-lg flex flex-col">
        <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex justify-between items-center">
          <h4 className="font-semibold text-neutral-900 dark:text-neutral-50">Swap exercise</h4>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="overflow-y-auto flex-1">
          {isLoading ? (
            <div className="px-6 py-4 text-neutral-600 dark:text-neutral-400">Loading…</div>
          ) : (data ?? []).length > 0 ? (
            <div className="divide-y divide-neutral-100 dark:divide-neutral-700">
              {(data ?? []).map((a) => (
                <button
                  key={a.id}
                  onClick={() => onPick(a.id)}
                  className="w-full px-6 py-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors text-neutral-900 dark:text-neutral-50 font-medium"
                >
                  {a.name}
                </button>
              ))}
            </div>
          ) : (
            <div className="px-6 py-4 text-neutral-600 dark:text-neutral-400">
              No alternatives available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
