import { Button } from './Button';
import type { Exercise } from '@/types/exercise';

interface ExercisePreviewModalProps {
  exercise: Exercise;
  onClose: () => void;
}

const difficultyColors: Record<string, string> = {
  Beginner: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  Intermediate: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  Advanced: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

export function ExercisePreviewModal({ exercise, onClose }: ExercisePreviewModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div
        className="bg-white dark:bg-neutral-800 rounded-lg max-w-sm w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-2">
                {exercise.name}
              </h2>
              <span
                className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                  difficultyColors[exercise.difficulty]
                }`}
              >
                {exercise.difficulty}
              </span>
            </div>
            <div className="relative w-16 h-16 bg-gray-200 dark:bg-neutral-700 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg
                className="w-8 h-8 text-teal-600 dark:text-teal-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50 mb-2 uppercase tracking-wide">
              Description
            </h3>
            <p className="text-neutral-600 dark:text-neutral-300 text-sm leading-relaxed">
              {exercise.description}
            </p>
          </div>

          {/* Target Muscles */}
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50 mb-3 uppercase tracking-wide">
              Target Muscles
            </h3>
            <div className="flex flex-wrap gap-2">
              {exercise.targetMuscles.map((muscle) => (
                <span
                  key={muscle}
                  className="px-3 py-1 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded-full text-xs font-semibold"
                >
                  {muscle}
                </span>
              ))}
            </div>
          </div>

          {/* Equipment */}
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50 mb-3 uppercase tracking-wide">
              Equipment
            </h3>
            <div className="px-3 py-2 bg-neutral-100 dark:bg-neutral-700/50 rounded-lg text-neutral-700 dark:text-neutral-300 text-sm font-medium">
              {exercise.equipment}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-neutral-200 dark:border-neutral-700">
          <Button type="button" variant="primary" onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
