import { useState, useEffect } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import { WEIGHT_UNIT_OPTIONS } from '@/types/programCreation';
import type { MatchRequest, WeightUnit } from '@/types/programCreation';

interface ProgramCreationFormProps {
  environmentId: number;
  onSubmit: (values: MatchRequest) => void;
  onCancel: () => void;
  initialValues?: MatchRequest;
}

export function ProgramCreationForm({
  environmentId,
  onSubmit,
  onCancel,
  initialValues,
}: ProgramCreationFormProps) {
  const [daysPerWeek, setDaysPerWeek] = useState(initialValues?.days_per_week.toString() ?? '3');
  const [sessionDurationMin, setSessionDurationMin] = useState(
    initialValues?.session_duration_min.toString() ?? '60',
  );
  const [weightUnit, setWeightUnit] = useState<WeightUnit>(initialValues?.weight_unit ?? 'kg');

  useEffect(() => {
    if (initialValues) {
      setDaysPerWeek(initialValues.days_per_week.toString());
      setSessionDurationMin(initialValues.session_duration_min.toString());
      setWeightUnit(initialValues.weight_unit);
    }
  }, [initialValues]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      environment_id: environmentId,
      days_per_week: parseInt(daysPerWeek, 10),
      session_duration_min: parseInt(sessionDurationMin, 10),
      weight_unit: weightUnit,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
        Generate a Program
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField
          label="Days per Week"
          type="number"
          name="days_per_week"
          value={daysPerWeek}
          onChange={(e) => setDaysPerWeek(e.target.value)}
          min="1"
          max="7"
          required
        />
        <FormField
          label="Session Duration (minutes)"
          type="number"
          name="session_duration_min"
          value={sessionDurationMin}
          onChange={(e) => setSessionDurationMin(e.target.value)}
          min="15"
          max="300"
          step="15"
          required
        />
        <div className="input-group">
          <label htmlFor="weight_unit" className="input-label">
            Weight Unit <span className="text-error-600">*</span>
          </label>
          <select
            id="weight_unit"
            name="weight_unit"
            value={weightUnit}
            onChange={(e) => setWeightUnit(e.target.value as WeightUnit)}
            required
          >
            {WEIGHT_UNIT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" className="flex-1">
          Next
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} className="flex-1">
          Cancel
        </Button>
      </div>
    </form>
  );
}
