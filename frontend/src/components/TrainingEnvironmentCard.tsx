import { Link } from 'react-router-dom';
import { Button } from './Button';
import { Card } from './Card';
import { ENVIRONMENT_TYPE_OPTIONS, EQUIPMENT_OPTIONS } from '@/types/trainingEnvironment';
import type { TrainingEnvironment } from '@/types/trainingEnvironment';

interface TrainingEnvironmentCardProps {
  environment: TrainingEnvironment;
  readOnly?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function TrainingEnvironmentCard({
  environment,
  readOnly = false,
  onEdit,
  onDelete,
}: TrainingEnvironmentCardProps) {
  const typeLabel =
    ENVIRONMENT_TYPE_OPTIONS.find((option) => option.value === environment.environment_type)
      ?.label ?? environment.environment_type;

  return (
    <Card padding="md" className="space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            {environment.name}
          </h3>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
              {typeLabel}
            </span>
            {environment.is_default && (
              <span className="text-xs px-2 py-1 rounded-full bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-100">
                Default
              </span>
            )}
          </div>
        </div>
      </div>

      {environment.equipment_tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {environment.equipment_tags.map((tag) => {
            const label = EQUIPMENT_OPTIONS.find((option) => option.value === tag)?.label ?? tag;
            return (
              <span
                key={tag}
                className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
              >
                {label}
              </span>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        {!readOnly && onEdit && (
          <Button variant="secondary" size="sm" onClick={onEdit}>
            Edit
          </Button>
        )}
        {!readOnly && onDelete && (
          <Button variant="danger" size="sm" onClick={onDelete}>
            Delete
          </Button>
        )}
        <Link
          to={`/programs/new/${environment.id}`}
          className="inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 px-3 py-1.5 text-sm bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800"
        >
          Generate Program
        </Link>
      </div>
    </Card>
  );
}
