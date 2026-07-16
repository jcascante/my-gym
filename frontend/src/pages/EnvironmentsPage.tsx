import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Spinner,
  TrainingEnvironmentCard,
  TrainingEnvironmentForm,
} from '@/components';
import {
  createTrainingEnvironment,
  deleteTrainingEnvironment,
  listTrainingEnvironments,
  updateTrainingEnvironment,
} from '@/api/trainingEnvironments';
import { getErrorMessage } from '@/api/errors';
import type { TrainingEnvironment, TrainingEnvironmentPayload } from '@/types/trainingEnvironment';

type PanelState = { mode: 'none' } | { mode: 'add' } | { mode: 'edit'; environmentId: number };

export default function EnvironmentsPage() {
  const [environments, setEnvironments] = useState<TrainingEnvironment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<PanelState>({ mode: 'none' });

  const loadEnvironments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTrainingEnvironments();
      setEnvironments(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadEnvironments();
  }, []);

  const handleCreate = async (payload: TrainingEnvironmentPayload) => {
    try {
      await createTrainingEnvironment(payload);
      setPanel({ mode: 'none' });
      await loadEnvironments();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleUpdate = async (environmentId: number, payload: TrainingEnvironmentPayload) => {
    try {
      await updateTrainingEnvironment(environmentId, payload);
      setPanel({ mode: 'none' });
      await loadEnvironments();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async (environmentId: number) => {
    if (!window.confirm('Delete this training environment? This cannot be undone.')) {
      return;
    }
    try {
      await deleteTrainingEnvironment(environmentId);
      await loadEnvironments();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">
          Training Environments
        </h1>
        {panel.mode === 'none' && (
          <Button variant="primary" onClick={() => setPanel({ mode: 'add' })}>
            Add Environment
          </Button>
        )}
      </div>

      {error && (
        <Alert type="error" dismissible onDismiss={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      {panel.mode === 'add' && (
        <div className="card p-6 mb-6">
          <TrainingEnvironmentForm
            onSubmit={handleCreate}
            onCancel={() => setPanel({ mode: 'none' })}
          />
        </div>
      )}

      {environments.length === 0 && panel.mode !== 'add' && (
        <p className="text-neutral-600 dark:text-neutral-400">
          You haven't added any training environments yet. Add one to describe where and how you
          train (e.g., a commercial gym, a home setup, or bodyweight-only).
        </p>
      )}

      <div className="space-y-4">
        {environments.map((environment) =>
          panel.mode === 'edit' && panel.environmentId === environment.id ? (
            <div key={environment.id} className="card p-6">
              <TrainingEnvironmentForm
                initialValues={environment}
                submitLabel="Save Changes"
                onSubmit={(payload) => handleUpdate(environment.id, payload)}
                onCancel={() => setPanel({ mode: 'none' })}
              />
            </div>
          ) : (
            <TrainingEnvironmentCard
              key={environment.id}
              environment={environment}
              onEdit={() => setPanel({ mode: 'edit', environmentId: environment.id })}
              onDelete={() => handleDelete(environment.id)}
            />
          ),
        )}
      </div>
    </div>
  );
}
