import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Stepper,
  TemplateMatchList,
  RequiredInputsForm,
  DraftProgramView,
  Button,
  ProgramWizard,
  Alert,
  Spinner,
} from '@/components';
import { useAcceptProgram, useCreateDraft, useInfiniteTemplateMatches } from '@/hooks/usePrograms';
import { useTrainingEnvironments } from '@/hooks/useTrainingEnvironments';
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
  const { environmentId: routeEnvironmentId } = useParams<{ environmentId?: string }>();
  const { userProfile } = useAuthStore();
  const [step, setStep] = useState(0);

  // No route param means the caller (e.g. the dashboard's "Create Program" shortcut)
  // didn't know which environment to use - resolve it from the user's own environments
  // instead of guessing an id that may not exist or belong to someone else.
  const environmentsQuery = useTrainingEnvironments({ enabled: !routeEnvironmentId });
  const resolvedEnvironmentId = useMemo(() => {
    if (routeEnvironmentId) return parseInt(routeEnvironmentId, 10);
    const environments = environmentsQuery.data ?? [];
    const defaultEnvironment = environments.find((environment) => environment.is_default);
    return (defaultEnvironment ?? environments[0])?.id ?? null;
  }, [routeEnvironmentId, environmentsQuery.data]);
  const [formPrefs, setFormPrefs] = useState<FormMatchRequest | null>(null);
  const [apiPrefs, setApiPrefs] = useState<ApiMatchRequest | null>(null);
  const [chosen, setChosen] = useState<TemplateMatch | null>(null);
  const [draft, setDraft] = useState<ProgramPreview | null>(null);
  const [requiredInputValues, setRequiredInputValues] = useState<Record<string, number | string>>(
    {},
  );

  const emptyRequest = useMemo(() => ({}) as ApiMatchRequest, []);
  const infiniteMatches = useInfiniteTemplateMatches(apiPrefs || emptyRequest);
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
    setStep(1);
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

  // Templates with no required_inputs skip the Details step entirely (onPick jumps
  // straight to step 3) - without this, the Stepper would show "Details" as a normal
  // completed step the user never saw, reading as a missed/glitched step rather than an
  // intentional skip.
  const detailsSkipped = step === 3 && chosen !== null && chosen.required_inputs.length === 0;

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
      <Stepper steps={STEPS} current={step} skipped={detailsSkipped ? [2] : []} />
      {step === 0 && !routeEnvironmentId && environmentsQuery.isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}
      {step === 0 &&
        !routeEnvironmentId &&
        !environmentsQuery.isLoading &&
        resolvedEnvironmentId === null && (
          <div>
            <Alert type="info" className="mb-4">
              You need to add a training environment before generating a program.
            </Alert>
            <Button variant="primary" onClick={() => navigate('/environments')}>
              Add a training environment
            </Button>
          </div>
        )}
      {step === 0 && resolvedEnvironmentId !== null && (
        <ProgramWizard
          environmentId={resolvedEnvironmentId}
          onComplete={onPrefs}
          onCancel={() => navigate(-1)}
        />
      )}
      {step === 1 && (
        <div>
          <TemplateMatchList
            matches={infiniteMatches.matches}
            selectedId={chosen?.template_id ?? null}
            onSelect={onPick}
            isLoading={infiniteMatches.isLoading}
            hasMore={infiniteMatches.hasMore}
            onLoadMore={infiniteMatches.fetchMore}
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
          {detailsSkipped && (
            <Alert type="info" className="mb-4">
              This template needed no extra details, so we generated your draft directly.
            </Alert>
          )}
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
