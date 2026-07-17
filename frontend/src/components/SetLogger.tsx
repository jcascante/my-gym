import { useState } from 'react';
import { Button } from '@/components';

export interface SetLoggerProps {
  exerciseName: string;
  suggestedWeight?: number;
  suggestedReps?: number;
  currentSet: number;
  totalSets: number;
  onLogSet: (weight: number, reps: number) => void;
  onSkipExercise?: () => void;
}

export function SetLogger({
  exerciseName,
  suggestedWeight = 0,
  suggestedReps = 8,
  currentSet,
  totalSets,
  onLogSet,
  onSkipExercise,
}: SetLoggerProps) {
  const [weight, setWeight] = useState<string>(suggestedWeight.toString());
  const [reps, setReps] = useState<string>(suggestedReps.toString());
  const [justLogged, setJustLogged] = useState(false);

  const handleLogSet = () => {
    const w = parseFloat(weight);
    const r = parseInt(reps, 10);

    if (isNaN(w) || w < 0 || isNaN(r) || r < 0) {
      return;
    }

    onLogSet(w, r);
    setJustLogged(true);
    setTimeout(() => setJustLogged(false), 500);
  };

  const isValid = weight && reps && !isNaN(parseFloat(weight)) && !isNaN(parseInt(reps, 10));

  return (
    <div className="space-y-6">
      {/* Exercise Header */}
      <div className="text-center">
        <h2 className="heading-lg mb-2">{exerciseName}</h2>
        <p className="label-sm text-neutral-600 dark:text-neutral-400">
          Set {currentSet} of {totalSets}
        </p>
      </div>

      {/* Input Fields */}
      <div className="space-y-4">
        {/* Weight Input */}
        <div className="flex flex-col">
          <label className="label-sm text-neutral-700 dark:text-neutral-300 mb-3">
            Weight (lbs)
          </label>
          <input
            type="number"
            inputMode="decimal"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="text-center text-5xl font-bold text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-transparent focus:outline-none focus:ring-0 font-variant-numeric tabular-nums"
            style={{ lineHeight: '1.2' }}
          />
        </div>

        {/* Reps Input */}
        <div className="flex flex-col">
          <label className="label-sm text-neutral-700 dark:text-neutral-300 mb-3">Reps</label>
          <input
            type="number"
            inputMode="numeric"
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            className="text-center text-5xl font-bold text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-transparent focus:outline-none focus:ring-0 font-variant-numeric tabular-nums"
            style={{ lineHeight: '1.2' }}
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-3 pt-4">
        <Button
          className={`w-full btn btn-success transition-all duration-300 ${
            justLogged ? 'scale-95 bg-success-700' : ''
          }`}
          onClick={handleLogSet}
          disabled={!isValid}
        >
          {justLogged ? '✓ Set Logged' : 'Log Set'}
        </Button>

        {onSkipExercise && (
          <Button className="w-full btn btn-outline" onClick={onSkipExercise}>
            Skip Exercise
          </Button>
        )}
      </div>
    </div>
  );
}
