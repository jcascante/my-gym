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
import { useAuthStore } from '@/store/auth';
import type { MatchRequest, ProgramPreview, TemplateMatch } from '@/types/program';
import type { MatchRequest as FormMatchRequest, WeightUnit } from '@/types/programCreation';

const STEPS = ['Preferences', 'Select', 'Details', 'Review'];

export default function ProgramBuilderPage() {
  const navigate = useNavigate();
  const { environmentId } = useParams<{ environmentId?: string }>();
  const { userProfile } = useAuthStore();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState<MatchRequest | null>(null);
  const [chosen, setChosen] = useState<TemplateMatch | null>(null);
  const [draft, setDraft] = useState<ProgramPreview | null>(null);
  const [requiredInputValues, setRequiredInputValues] = useState<Record<string, number | string>>(
    {},
  );

  const match = useMatchTemplates();
  const createDraft = useCreateDraft();
  const accept = useAcceptProgram(draft?.program_id ?? 0);

  const onPrefs = (values: FormMatchRequest) => {
    // Adapt form output (4 fields) to MatchRequest (6 fields)
    const matchRequest: MatchRequest = {
      ...values,
      fitness_focus: userProfile?.fitness_focus || 'general',
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
    setRequiredInputValues(requiredInputs);
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

  const handleBack = () => {
    if (step === 3 && chosen && chosen.required_inputs.length === 0) {
      setStep(1);
      return;
    }
    if (step === 2) {
      setRequiredInputValues({});
    }
    setStep(step - 1);
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <Stepper steps={STEPS} current={step} />
      {step === 0 && (
        <ProgramCreationForm
          environmentId={parseInt(environmentId || '1', 10)}
          onSubmit={onPrefs}
          onCancel={() => navigate(-1)}
          initialValues={
            prefs
              ? {
                  environment_id: prefs.environment_id,
                  days_per_week: prefs.days_per_week,
                  session_duration_min: prefs.session_duration_min,
                  weight_unit: prefs.weight_unit as WeightUnit,
                }
              : undefined
          }
        />
      )}
      {step === 1 && (
        <div>
          <TemplateMatchList
            matches={match.data ?? []}
            selectedId={chosen?.template_id ?? null}
            onSelect={onPick}
          />
          <div className="mt-6 flex gap-3 justify-between">
            <Button variant="secondary" onClick={handleBack}>
              Back
            </Button>
          </div>
        </div>
      )}
      {step === 2 && chosen && (
        <div>
          <RequiredInputsForm
            inputs={chosen.required_inputs}
            onSubmit={(v) => makeDraft(chosen, v)}
            initialValues={requiredInputValues}
          />
          <div className="mt-6 flex gap-3 justify-between">
            <Button variant="secondary" onClick={handleBack}>
              Back
            </Button>
            <Button form="required-inputs-form" type="submit" variant="primary">
              Next
            </Button>
          </div>
        </div>
      )}
      {step === 3 && draft && (
        <div>
          <DraftProgramView program={draft} programId={draft.program_id} />
          <div className="mt-6 flex gap-3 justify-between">
            <Button variant="secondary" onClick={handleBack}>
              Back
            </Button>
            <Button variant="primary" onClick={onAccept}>
              Accept program
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
