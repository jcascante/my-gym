import React, { useEffect, useRef, useState } from 'react';
import type { EffortMethod, WeightUnit } from '../types/programCreation';
import type { EffortTarget } from '../types/program';
import { Button } from './Button';
import { FormField } from './FormField';
import { formatEffortDisplay } from '../utils/effortDisplay';
import type { LoggedSetEntry } from '../hooks/useSessionProgress';

interface SetRowProps {
  setNumber: number;
  effort_method: EffortMethod;
  weightUnit: WeightUnit;
  loggedSet?: LoggedSetEntry;
  // Scopes this row's input ids (e.g. to the owning exercise) so two rows sharing
  // a setNumber never collide on DOM id when both render at once - as happens once
  // multiple exercise sections can be open simultaneously.
  idPrefix?: string | number;
  onLogSet: (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => Promise<void> | void;
}

function getEffortBounds(effort_method: EffortMethod) {
  switch (effort_method) {
    case 'rpe':
      return { min: 1, max: 10, label: 'RPE (1–10)', short: 'RPE' };
    case 'rir':
      return { min: 0, max: 10, label: 'Reps in Reserve (0–10)', short: 'RIR' };
    case 'borg':
      return { min: 6, max: 20, label: 'Borg Scale (6–20) - Perceived Exertion', short: 'Borg' };
    default:
      return { min: 1, max: 10, label: 'RPE (1–10)', short: 'RPE' };
  }
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export const SetRow: React.FC<SetRowProps> = ({
  setNumber,
  effort_method,
  weightUnit,
  loggedSet,
  idPrefix,
  onLogSet,
}) => {
  const idScope = idPrefix !== undefined ? `${idPrefix}-${setNumber}` : `${setNumber}`;
  const [mode, setMode] = useState<'summary' | 'edit'>(loggedSet ? 'summary' : 'edit');
  const [weight, setWeight] = useState<number | ''>(loggedSet?.weight ?? '');
  const [reps, setReps] = useState<number | ''>(loggedSet?.reps ?? '');
  const [effort, setEffort] = useState<number | ''>(loggedSet?.effort ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { min, max, label } = getEffortBounds(effort_method);

  const hadLoggedSetRef = useRef(Boolean(loggedSet));
  useEffect(() => {
    if (!hadLoggedSetRef.current && loggedSet) {
      setMode('summary');
    }
    hadLoggedSetRef.current = Boolean(loggedSet);
  }, [loggedSet]);

  const handleWeightBlur = () => {
    if (weight !== '' && weight < 0) setWeight('');
  };

  const handleRepsBlur = () => {
    if (reps !== '' && (reps < 1 || reps > 100)) setReps('');
  };

  const handleEffortBlur = () => {
    if (effort !== '') setEffort(clamp(Number(effort), min, max));
  };

  const handleEditTap = () => {
    if (!loggedSet) return;
    setWeight(loggedSet.weight ?? '');
    setReps(loggedSet.reps ?? '');
    setEffort(loggedSet.effort ?? '');
    setMode('edit');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (effort === '' || isSubmitting) return;

    const effortVal = clamp(Number(effort), min, max);

    setIsSubmitting(true);
    try {
      await onLogSet({
        weight: weight !== '' ? weight : undefined,
        reps: reps !== '' ? reps : undefined,
        effort: effortVal,
        effort_method,
      });
      setMode('summary');
    } catch {
      // Stay in edit mode with the entered values so the user can retry - the
      // caller is responsible for surfacing the failure (e.g. a toast).
    } finally {
      setIsSubmitting(false);
    }
  };

  if (mode === 'summary' && loggedSet) {
    const performedEffortTarget: EffortTarget | null =
      loggedSet.effort !== undefined && loggedSet.effort_method
        ? { method: loggedSet.effort_method, value: loggedSet.effort }
        : null;

    const performedDisplay = formatEffortDisplay(
      1,
      loggedSet.reps ?? 0,
      loggedSet.weight ?? null,
      weightUnit,
      performedEffortTarget,
    );

    return (
      <button
        type="button"
        onClick={handleEditTap}
        aria-label={`Set ${setNumber} logged, tap to edit`}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-success-50 dark:bg-success-900 border border-success-200 dark:border-success-700 text-left"
      >
        <span className="text-body-sm font-variant-numeric tabular-nums">
          Set {setNumber} · {performedDisplay}
        </span>
        <span className="text-success-600 dark:text-success-400 text-sm shrink-0">
          ✓ tap to edit
        </span>
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-1 md:space-y-2 rounded-lg border border-neutral-200 dark:border-neutral-700 p-2 md:p-3"
    >
      <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
        Set {setNumber}
      </p>
      <div className="grid grid-cols-3 gap-1 md:gap-2">
        <FormField
          id={`weight-input-${idScope}`}
          label="Weight"
          type="number"
          step="0.5"
          value={weight}
          onChange={(e) => setWeight(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleWeightBlur}
          placeholder="0"
          groupClassName="mb-0 md:mb-4"
          labelClassName="text-xs md:text-sm mb-1 md:mb-2"
          className="px-2 py-1 md:px-3 md:py-2 text-base"
        />
        <FormField
          id={`reps-input-${idScope}`}
          label="Reps"
          type="number"
          value={reps}
          onChange={(e) => setReps(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleRepsBlur}
          placeholder="0"
          groupClassName="mb-0 md:mb-4"
          labelClassName="text-xs md:text-sm mb-1 md:mb-2"
          className="px-2 py-1 md:px-3 md:py-2 text-base"
        />
        <FormField
          id={`effort-input-${idScope}`}
          label={label}
          type="number"
          step={effort_method === 'rpe' ? 0.5 : 1}
          value={effort}
          onChange={(e) => setEffort(e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={handleEffortBlur}
          placeholder="0"
          required
          groupClassName="mb-0 md:mb-4"
          labelClassName="text-xs md:text-sm mb-1 md:mb-2"
          className="px-2 py-1 md:px-3 md:py-2 text-base"
        />
      </div>
      <Button
        type="submit"
        variant="primary"
        disabled={effort === '' || isSubmitting}
        className="w-full"
      >
        Log Set {setNumber}
      </Button>
    </form>
  );
};
