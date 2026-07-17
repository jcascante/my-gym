import { Button } from '@/components';

export interface ProgramGridCardProps {
  id: number;
  name: string;
  duration_weeks: number;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  daysPerWeek?: number;
  isActive?: boolean;
  onSelect: (id: number) => void;
  onStart?: (id: number) => void;
}

const difficultyBadgeClasses = {
  beginner: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300',
  intermediate: 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300',
  advanced: 'bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-300',
};

export function ProgramGridCard({
  id,
  name,
  duration_weeks,
  difficulty = 'intermediate',
  daysPerWeek = 4,
  isActive = false,
  onSelect,
  onStart,
}: ProgramGridCardProps) {
  const borderClass = isActive
    ? 'border-2 border-primary-600'
    : 'border border-neutral-200 dark:border-neutral-700';
  const bgClass = isActive ? 'bg-primary-50 dark:bg-primary-900/10' : '';

  return (
    <div
      onClick={() => onSelect(id)}
      className={`card rounded-lg p-6 cursor-pointer transition-all hover:shadow-md ${borderClass} ${bgClass}`}
    >
      {/* Header */}
      <div className="mb-4">
        <h3 className="heading-md mb-2">{name}</h3>

        {/* Difficulty Badge */}
        <div className="inline-block">
          <span
            className={`label-sm px-3 py-1 rounded-full text-xs ${difficultyBadgeClasses[difficulty]}`}
          >
            {difficulty}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-3 mb-6">
        <div className="flex items-center gap-2 text-body-sm text-neutral-600 dark:text-neutral-400">
          <span>⏱️</span>
          <span>{duration_weeks} weeks</span>
        </div>

        <div className="flex items-center gap-2 text-body-sm text-neutral-600 dark:text-neutral-400">
          <span>📅</span>
          <span>{daysPerWeek} days/week</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex gap-2">
        {isActive ? (
          <div className="flex-1 py-2 px-4 bg-success-50 dark:bg-success-900/20 rounded-lg text-center">
            <p className="label-sm text-success-700 dark:text-success-300">Active</p>
          </div>
        ) : (
          <Button
            className="flex-1 btn btn-primary"
            onClick={(e) => {
              e.stopPropagation();
              onStart?.(id);
            }}
          >
            Start
          </Button>
        )}
      </div>
    </div>
  );
}
