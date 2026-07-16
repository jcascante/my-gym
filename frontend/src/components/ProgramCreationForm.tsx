import { useState, useEffect } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import {
  WEIGHT_UNIT_OPTIONS,
  PROGRESSION_STYLE_OPTIONS,
  EFFORT_METHOD_OPTIONS,
  EQUIPMENT_FAMILY_OPTIONS,
  VARIETY_PREFERENCE_OPTIONS,
} from '@/types/programCreation';
import type {
  MatchRequest,
  WeightUnit,
  ProgressionStyle,
  EffortMethod,
  EquipmentFamily,
  VarietyPreference,
} from '@/types/programCreation';

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
  const [progressionStyle, setProgressionStyle] = useState<ProgressionStyle>(
    initialValues?.progression_style ?? 'consistent',
  );
  const [effortMethod, setEffortMethod] = useState<EffortMethod | ''>(
    initialValues?.effort_method ?? '',
  );
  const [movementPreferences, setMovementPreferences] = useState<Record<EquipmentFamily, number>>(
    initialValues?.movement_preferences ?? {
      dumbbells: 50,
      barbells: 50,
      machines: 50,
      bodyweight: 50,
      cables: 50,
      kettlebells: 50,
    },
  );
  const [complementaryFocus, setComplementaryFocus] = useState<boolean>(
    initialValues?.complementary_focus ?? true,
  );
  const [varietyPreference, setVarietyPreference] = useState<VarietyPreference>(
    initialValues?.variety_preference ?? 'low',
  );

  useEffect(() => {
    if (initialValues) {
      setDaysPerWeek(initialValues.days_per_week.toString());
      setSessionDurationMin(initialValues.session_duration_min.toString());
      setWeightUnit(initialValues.weight_unit);
      setProgressionStyle(initialValues.progression_style);
      setEffortMethod(initialValues.effort_method);
      if (initialValues.movement_preferences) {
        setMovementPreferences(initialValues.movement_preferences);
      }
      if (initialValues.complementary_focus !== undefined) {
        setComplementaryFocus(initialValues.complementary_focus);
      }
      if (initialValues.variety_preference) {
        setVarietyPreference(initialValues.variety_preference);
      }
    }
  }, [initialValues]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      environment_id: environmentId,
      days_per_week: parseInt(daysPerWeek, 10),
      session_duration_min: parseInt(sessionDurationMin, 10),
      weight_unit: weightUnit,
      progression_style: progressionStyle,
      effort_method: effortMethod,
      movement_preferences: movementPreferences,
      complementary_focus: complementaryFocus,
      variety_preference: varietyPreference,
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
        <div className="input-group">
          <label htmlFor="progression_style" className="input-label">
            Progression Style <span className="text-error-600">*</span>
          </label>
          <select
            id="progression_style"
            name="progression_style"
            value={progressionStyle}
            onChange={(e) => setProgressionStyle(e.target.value as ProgressionStyle)}
            required
          >
            {PROGRESSION_STYLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="input-group">
          <label htmlFor="effort_method" className="input-label">
            Effort Tracking Style
          </label>
          <select
            id="effort_method"
            name="effort_method"
            value={effortMethod}
            onChange={(e) => setEffortMethod(e.target.value as EffortMethod | '')}
          >
            {EFFORT_METHOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <div>
          <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50 mb-3">
            Equipment Preferences
          </h4>
          <div className="space-y-3">
            {EQUIPMENT_FAMILY_OPTIONS.map((option) => (
              <div key={option.value} className="flex items-center gap-3">
                <label
                  htmlFor={`pref_${option.value}`}
                  className="text-sm text-neutral-700 dark:text-neutral-300 w-24"
                >
                  {option.label}
                </label>
                <input
                  id={`pref_${option.value}`}
                  type="range"
                  min="0"
                  max="100"
                  value={movementPreferences[option.value]}
                  onChange={(e) =>
                    setMovementPreferences({
                      ...movementPreferences,
                      [option.value]: parseInt(e.target.value, 10),
                    })
                  }
                  className="flex-1 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer"
                />
                <span className="text-sm text-neutral-600 dark:text-neutral-400 w-8 text-right">
                  {movementPreferences[option.value]}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <input
            id="complementary_focus"
            type="checkbox"
            checked={complementaryFocus}
            onChange={(e) => setComplementaryFocus(e.target.checked)}
            className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600 focus:ring-primary-500"
          />
          <label
            htmlFor="complementary_focus"
            className="text-sm text-neutral-900 dark:text-neutral-50"
          >
            Include complementary exercises (isolation work)
          </label>
        </div>

        <div className="input-group">
          <label htmlFor="variety_preference" className="input-label">
            Exercise Variety
          </label>
          <select
            id="variety_preference"
            name="variety_preference"
            value={varietyPreference}
            onChange={(e) => setVarietyPreference(e.target.value as VarietyPreference)}
          >
            {VARIETY_PREFERENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        <Button type="button" variant="secondary" onClick={onCancel} className="flex-1">
          Cancel
        </Button>
        <Button type="submit" variant="primary" className="flex-1">
          Next
        </Button>
      </div>
    </form>
  );
}
