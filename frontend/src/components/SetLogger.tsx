import React, { useState } from 'react';
import { EffortMethod } from '../types/programCreation';
import { Button } from './Button';
import { FormField } from './FormField';

interface SetLoggerProps {
  effort_method: EffortMethod;
  onSetLogged: (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => void;
}

export const SetLogger: React.FC<SetLoggerProps> = ({ effort_method, onSetLogged }) => {
  const [weight, setWeight] = useState<number | ''>('');
  const [reps, setReps] = useState<number | ''>('');
  const [effort, setEffort] = useState<number | ''>('');

  const getEffortBounds = () => {
    switch (effort_method) {
      case 'rpe':
        return { min: 1, max: 10, label: 'RPE (1–10)' };
      case 'rir':
        return { min: 0, max: 10, label: 'Reps in Reserve (0–10)' };
      case 'borg':
        return { min: 6, max: 20, label: 'Borg Scale (6–20) - Perceived Exertion' };
      default:
        return { min: 1, max: 10, label: 'RPE (1–10)' };
    }
  };

  const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

  const handleWeightBlur = () => {
    if (weight !== '' && weight < 0) setWeight('');
  };

  const handleRepsBlur = () => {
    if (reps !== '' && (reps < 1 || reps > 100)) setReps('');
  };

  const handleEffortBlur = () => {
    if (effort !== '') {
      const { min, max } = getEffortBounds();
      setEffort(clamp(Number(effort), min, max));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (effort === '') return;

    const { min, max } = getEffortBounds();
    const effortVal = clamp(Number(effort), min, max);

    onSetLogged({
      weight: weight !== '' ? weight : undefined,
      reps: reps !== '' ? reps : undefined,
      effort: effortVal,
      effort_method,
    });

    // Reset form
    setWeight('');
    setReps('');
    setEffort('');
  };

  const { label } = getEffortBounds();

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <FormField
        id="weight-input"
        label="Weight (optional)"
        type="number"
        step="0.5"
        value={weight}
        onChange={(e) => setWeight(e.target.value === '' ? '' : Number(e.target.value))}
        onBlur={handleWeightBlur}
        placeholder="0"
      />

      <FormField
        id="reps-input"
        label="Reps (optional)"
        type="number"
        value={reps}
        onChange={(e) => setReps(e.target.value === '' ? '' : Number(e.target.value))}
        onBlur={handleRepsBlur}
        placeholder="0"
      />

      <FormField
        id="effort-input"
        label={label}
        type="number"
        step={effort_method === 'rpe' ? 0.5 : 1}
        value={effort}
        onChange={(e) => setEffort(e.target.value === '' ? '' : Number(e.target.value))}
        onBlur={handleEffortBlur}
        placeholder="0"
      />

      <Button type="submit" variant="primary" disabled={effort === ''} className="w-full">
        Log Set
      </Button>
    </form>
  );
};
