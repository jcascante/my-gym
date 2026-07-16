import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Stepper,
  TemplateMatchList,
  RequiredInputsForm,
  DraftProgramView,
  Button,
} from '@/components';
import { ProgramCreationForm } from '@/components/ProgramCreationForm';
import { useAcceptProgram, useCreateDraft, useMatchTemplates } from '@/hooks/usePrograms';
import type { MatchRequest, ProgramPreview, TemplateMatch } from '@/types/program';
import type { MatchRequest as FormMatchRequest } from '@/types/programCreation';

const STEPS = ['Preferences', 'Select', 'Details', 'Review'];

export default function ProgramBuilderPage() {
  const navigate = useNavigate();
  const { environmentId } = useParams<{ environmentId?: string }>();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState<MatchRequest | null>(null);
  const [chosen, setChosen] = useState<TemplateMatch | null>(null);
  const [draft, setDraft] = useState<ProgramPreview | null>(null);

  const match = useMatchTemplates();
  const createDraft = useCreateDraft();
  const accept = useAcceptProgram(draft?.program_id ?? 0);

  const onPrefs = (values: FormMatchRequest) => {
    // Adapt form output (4 fields) to MatchRequest (6 fields)
    const matchRequest: MatchRequest = {
      ...values,
      fitness_focus: 'full_body',
      duration_weeks: 8,
    };
    setPrefs(matchRequest);
    match.mutate(matchRequest, { onSuccess: () => setStep(1) });
  };

  const onPick = (m: TemplateMatch) => {
    setChosen(m);
    if (m.required_inputs.length > 0) {
      setStep(2);
      return;
    }
    void makeDraft(m, {});
  };

  const makeDraft = async (m: TemplateMatch, requiredInputs: Record<string, number | string>) => {
    if (!prefs) return;
    const program = await createDraft.mutateAsync({
      ...prefs,
      template_id: m.template_id,
      required_inputs: requiredInputs,
    });
    setDraft(program);
    setStep(3);
  };

  const onAccept = async () => {
    const accepted = await accept.mutateAsync();
    navigate(`/programs/${accepted.program_id}`);
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <Stepper steps={STEPS} current={step} />
      {step === 0 && (
        <ProgramCreationForm
          environmentId={parseInt(environmentId || '1', 10)}
          onSubmit={onPrefs}
          onCancel={() => navigate(-1)}
        />
      )}
      {step === 1 && (
        <TemplateMatchList
          matches={match.data ?? []}
          selectedId={chosen?.template_id ?? null}
          onSelect={onPick}
        />
      )}
      {step === 2 && chosen && (
        <RequiredInputsForm
          inputs={chosen.required_inputs}
          onSubmit={(v) => makeDraft(chosen, v)}
        />
      )}
      {step === 3 && draft && (
        <div>
          <DraftProgramView program={draft} programId={draft.program_id} />
          <div className="mt-6 flex justify-end">
            <Button onClick={onAccept}>Accept program</Button>
          </div>
        </div>
      )}
    </div>
  );
}
