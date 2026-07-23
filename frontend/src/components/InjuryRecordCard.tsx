import { Button } from './Button';
import { Card } from './Card';
import {
  INJURY_CONDITION_OPTIONS,
  INJURY_PHASE_OPTIONS,
  INJURY_REGION_OPTIONS,
  PROVOCATION_OPTIONS,
  SEVERITY_OPTIONS,
} from '@/types/injury';
import type { InjuryRecord } from '@/types/injury';

interface InjuryRecordCardProps {
  injury: InjuryRecord;
  onDelete?: () => void;
}

function labelFor<T extends string | number>(
  options: { value: T; label: string }[],
  value: T,
): string {
  return options.find((option) => option.value === value)?.label ?? String(value);
}

export function InjuryRecordCard({ injury, onDelete }: InjuryRecordCardProps) {
  return (
    <Card padding="md" className="space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            {labelFor(INJURY_REGION_OPTIONS, injury.region)}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
              {labelFor(INJURY_CONDITION_OPTIONS, injury.condition)}
            </span>
            <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
              {labelFor(INJURY_PHASE_OPTIONS, injury.phase)}
            </span>
            <span className="text-xs px-2 py-1 rounded-full bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-100">
              {labelFor(SEVERITY_OPTIONS, injury.severity)}
            </span>
          </div>
        </div>
      </div>

      {injury.provocations.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {injury.provocations.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
            >
              {labelFor(PROVOCATION_OPTIONS, tag)}
            </span>
          ))}
        </div>
      )}

      <p className="text-xs text-neutral-500 dark:text-neutral-400">
        Reported {injury.reported_at}
      </p>

      {onDelete && (
        <div className="pt-1">
          <Button variant="danger" size="sm" onClick={onDelete}>
            Remove
          </Button>
        </div>
      )}
    </Card>
  );
}
