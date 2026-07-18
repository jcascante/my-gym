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

interface ProgramWizardStep1Props {
  environmentId: number;
  onSubmit: (values: MatchRequest) => void;
  onCancel: () => void;
  initialValues?: MatchRequest;
}

export function ProgramWizardStep1({
  environmentId,
  onSubmit,
  onCancel,
  initialValues,
}: ProgramWizardStep1Props) {
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

  const handleDaysChange = (delta: number) => {
    const current = parseInt(daysPerWeek, 10);
    const newValue = Math.max(1, Math.min(7, current + delta));
    setDaysPerWeek(newValue.toString());
  };

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
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-1">
          Generate Your Program
        </h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Let's customize your personalized workout plan
        </p>
      </div>

      <div className="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-3 text-center text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
        Preferences
      </div>

      <div className="space-y-4">
        {/* Days per Week Stepper */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            Days per Week <span className="text-error-600">*</span>
          </label>
          <div className="flex items-center justify-between bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
            <button
              type="button"
              onClick={() => handleDaysChange(-1)}
              className="w-10 h-10 flex items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 hover:border-teal-500 dark:hover:border-teal-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors active:scale-90"
              aria-label="Decrease days per week"
            >
              −
            </button>
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">
                {daysPerWeek}
              </span>
              <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Days
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleDaysChange(1)}
              className="w-10 h-10 flex items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 hover:border-teal-500 dark:hover:border-teal-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors active:scale-90"
              aria-label="Increase days per week"
            >
              +
            </button>
          </div>
        </div>

        {/* Session Duration */}
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

        {/* Weight Unit */}
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

        {/* Progression Style */}
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

        {/* Effort Tracking Style */}
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

      <div className="mt-6 space-y-4 border-t border-neutral-200 dark:border-neutral-700 pt-6">
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

      {/* Action Buttons */}
      <div className="flex gap-3 pt-6">
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
