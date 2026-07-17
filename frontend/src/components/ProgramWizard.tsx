import { useState } from 'react';
import { ProgramWizardStep1 } from './ProgramWizardStep1';
import { ExerciseSelection } from './ExerciseSelection';
import type { MatchRequest } from '@/types/programCreation';

interface ProgramWizardProps {
  environmentId: number;
  onCancel: () => void;
  onComplete: (values: MatchRequest) => void;
}

export function ProgramWizard({ environmentId, onCancel, onComplete }: ProgramWizardProps) {
  const [step, setStep] = useState(1);
  const [formValues, setFormValues] = useState<MatchRequest | null>(null);

  const handleStep1Submit = (values: MatchRequest) => {
    setFormValues(values);
    setStep(2);
  };

  const handleStep2Complete = () => {
    if (formValues) {
      onComplete(formValues);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  return (
    <div className="w-full">
      {step === 1 ? (
        <ProgramWizardStep1
          environmentId={environmentId}
          onSubmit={handleStep1Submit}
          onCancel={onCancel}
          initialValues={formValues ?? undefined}
        />
      ) : (
        <ExerciseSelection onComplete={() => handleStep2Complete()} onBack={handleBack} />
      )}
    </div>
  );
}
