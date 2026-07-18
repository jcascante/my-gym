import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Stepper,
  TemplateMatchList,
  RequiredInputsForm,
  DraftProgramView,
  Button,
  ProgramWizard,
} from '@/components';
import { useAcceptProgram, useCreateDraft, useMatchTemplates } from '@/hooks/usePrograms';
import { useAuthStore } from '@/store/auth';
import type {
  MatchRequest as ApiMatchRequest,
  ProgramPreview,
  TemplateMatch,
} from '@/types/program';
import type { MatchRequest as FormMatchRequest } from '@/types/programCreation';

const STEPS = ['Preferences', 'Select', 'Details', 'Review'];

export default function ProgramBuilderPage() {
  const navigate = useNavigate();
  const { environmentId } = useParams<{ environmentId?: string }>();
  const { userProfile } = useAuthStore();
  const [step, setStep] = useState(0);
  const [formPrefs, setFormPrefs] = useState<FormMatchRequest | null>(null);
  const [apiPrefs, setApiPrefs] = useState<ApiMatchRequest | null>(null);
  const [chosen, setChosen] = useState<TemplateMatch | null>(null);
  const [draft, setDraft] = useState<ProgramPreview | null>(null);
  const [requiredInputValues, setRequiredInputValues] = useState<Record<string, number | string>>(
    {},
  );

  const match = useMatchTemplates();
  const createDraft = useCreateDraft();
  const accept = useAcceptProgram(draft?.program_id ?? 0);

  const onPrefs = (values: FormMatchRequest) => {
    setFormPrefs(values);
    const fitnessFocus = userProfile?.fitness_focus || 'general';
    const apiRequest: ApiMatchRequest = {
      environment_id: values.environment_id,
      days_per_week: values.days_per_week,
      session_duration_min: values.session_duration_min,
      weight_unit: values.weight_unit,
      fitness_focus: fitnessFocus,
      duration_weeks: 8,
    };
    setApiPrefs(apiRequest);
    match.mutate(apiRequest, { onSuccess: () => setStep(1) });
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
    if (!apiPrefs || !formPrefs) return;
    setRequiredInputValues(requiredInputs);
    const program = await createDraft.mutateAsync({
      ...apiPrefs,
      template_id: m.template_id,
      required_inputs: requiredInputs,
      progression_style: formPrefs.progression_style,
      effort_method: formPrefs.effort_method || null,
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
        <ProgramWizard
          environmentId={parseInt(environmentId || '1', 10)}
          onComplete={onPrefs}
          onCancel={() => navigate(-1)}
        />
      )}
      {step === 1 && (
        <div>
          <TemplateMatchList
            matches={match.data ?? []}
            selectedId={chosen?.template_id ?? null}
            onSelect={onPick}
          />
          <div className="mt-6 flex gap-3">
            <Button type="button" variant="secondary" onClick={handleBack} className="flex-1">
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
          <div className="mt-6 flex gap-3">
            <Button type="button" variant="secondary" onClick={handleBack} className="flex-1">
              Back
            </Button>
            <Button form="required-inputs-form" type="submit" variant="primary" className="flex-1">
              Next
            </Button>
          </div>
        </div>
      )}
      {step === 3 && draft && (
        <div>
          <DraftProgramView program={draft} programId={draft.program_id} />
          <div className="mt-6 flex gap-3">
            <Button type="button" variant="secondary" onClick={handleBack} className="flex-1">
              Back
            </Button>
            <Button type="button" variant="primary" onClick={onAccept} className="flex-1">
              Accept program
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
