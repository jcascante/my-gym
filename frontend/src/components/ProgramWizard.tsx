import { ProgramWizardStep1 } from './ProgramWizardStep1';
import type { MatchRequest } from '@/types/programCreation';

interface ProgramWizardProps {
  environmentId: number;
  onCancel: () => void;
  onComplete: (values: MatchRequest) => void;
}

export function ProgramWizard({ environmentId, onCancel, onComplete }: ProgramWizardProps) {
  return (
    <ProgramWizardStep1 environmentId={environmentId} onSubmit={onComplete} onCancel={onCancel} />
  );
}
