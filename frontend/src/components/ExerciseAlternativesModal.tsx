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
      <div className="bg-white rounded-lg p-4 w-80 max-h-[70vh] overflow-y-auto">
        <div className="flex justify-between mb-2">
          <h4 className="font-semibold">Swap exercise</h4>
          <button aria-label="close" onClick={onClose}>
            ✕
          </button>
        </div>
        {isLoading ? (
          <p>Loading…</p>
        ) : (
          (data ?? []).map((a) => (
            <button
              key={a.id}
              className="block w-full text-left px-2 py-2 hover:bg-gray-50"
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
