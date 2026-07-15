import { useState } from 'react';
import { Alert } from './Alert';
import { Button } from './Button';
import { FormField } from './FormField';
import { createProgram } from '@/api/programs';
import {
  DAY_OF_WEEK_OPTIONS,
  FOCUS_AREA_OPTIONS,
  PROGRESSION_STYLE_OPTIONS,
  WEIGHT_UNIT_OPTIONS,
} from '@/types/programCreation';
import type { DayOfWeek, FocusArea, ProgressionStyle, WeightUnit } from '@/types/programCreation';

interface ProgramCreationFormProps {
  environmentId: number;
  onCancel: () => void;
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ProgramCreationForm({ environmentId, onCancel }: ProgramCreationFormProps) {
  const [daysPerWeek, setDaysPerWeek] = useState('3');
  const [preferredDays, setPreferredDays] = useState<DayOfWeek[]>([]);
  const [sessionDurationMin, setSessionDurationMin] = useState('60');
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([]);
  const [weightUnit, setWeightUnit] = useState<WeightUnit>('kg');
  const [weightIncrements, setWeightIncrements] = useState('1.25, 2.5, 5');
  const [progressionStyle, setProgressionStyle] = useState<ProgressionStyle>('consistent');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const toggleDay = (day: DayOfWeek) => {
    setPreferredDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  };

  const toggleFocusArea = (area: FocusArea) => {
    setFocusAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResult(null);
    setSubmitting(true);

    try {
      await createProgram({
        environment_id: environmentId,
        days_per_week: parseInt(daysPerWeek, 10),
        preferred_days: preferredDays,
        session_duration_min: parseInt(sessionDurationMin, 10),
        start_date: startDate,
        focus_areas: focusAreas,
        weight_unit: weightUnit,
        available_weight_increments: weightIncrements
          .split(',')
          .map((v) => parseFloat(v.trim()))
          .filter((v) => !Number.isNaN(v)),
        progression_style: progressionStyle,
      });
      // The backend always returns 501 for now — a real 2xx would mean
      // program generation shipped and this message needs to change.
      setResult({
        type: 'success',
        message: 'Program generation is coming soon — your preferences were recorded.',
      });
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 501) {
        setResult({
          type: 'success',
          message: 'Program generation is coming soon — your preferences were recorded.',
        });
      } else {
        setResult({
          type: 'error',
          message: 'Something went wrong recording your preferences. Please try again.',
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
        Generate a Program
      </h3>

      {result && (
        <Alert type={result.type} dismissible onDismiss={() => setResult(null)}>
          {result.message}
        </Alert>
      )}

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
        <FormField
          label="Start Date"
          type="date"
          name="start_date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
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

      <div>
        <span className="input-label block mb-2">Preferred Days</span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {DAY_OF_WEEK_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={preferredDays.includes(option.value)}
                onChange={() => toggleDay(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <div>
        <span className="input-label block mb-2">Focus Areas</span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {FOCUS_AREA_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={focusAreas.includes(option.value)}
                onChange={() => toggleFocusArea(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <FormField
        label="Available Weight Increments (comma-separated)"
        name="available_weight_increments"
        value={weightIncrements}
        onChange={(e) => setWeightIncrements(e.target.value)}
        placeholder="e.g., 1.25, 2.5, 5"
        hint="The smallest jumps you can actually load, so progression suggestions stay realistic."
      />

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

      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" isLoading={submitting} className="flex-1">
          Generate Program
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={submitting}
          className="flex-1"
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
