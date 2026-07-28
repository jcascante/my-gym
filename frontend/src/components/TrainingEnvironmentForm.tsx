import { useState } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import { EquipmentPicker } from './EquipmentPicker';
import {
  ENVIRONMENT_TYPE_OPTIONS,
  ENVIRONMENT_EQUIPMENT_PRESETS,
} from '@/types/trainingEnvironment';
import type { TrainingEnvironmentPayload } from '@/types/trainingEnvironment';

interface TrainingEnvironmentFormProps {
  initialValues?: Partial<TrainingEnvironmentPayload>;
  onSubmit: (payload: TrainingEnvironmentPayload) => void | Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

export function TrainingEnvironmentForm({
  initialValues,
  onSubmit,
  onCancel,
  submitLabel = 'Save Environment',
}: TrainingEnvironmentFormProps) {
  const [name, setName] = useState(initialValues?.name ?? '');
  const [environmentType, setEnvironmentType] = useState(initialValues?.environment_type ?? 'home');
  const [equipmentTags, setEquipmentTags] = useState<string[]>(initialValues?.equipment_tags ?? []);
  const [isDefault, setIsDefault] = useState(initialValues?.is_default ?? false);
  const [submitting, setSubmitting] = useState(false);

  const handleEnvironmentTypeChange = (newType: typeof environmentType) => {
    setEnvironmentType(newType);
    // Prefill with the archetype's typical equipment, but don't clobber tags
    // the user already picked (e.g. when editing an existing environment).
    if (equipmentTags.length === 0) {
      setEquipmentTags(ENVIRONMENT_EQUIPMENT_PRESETS[newType]);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        name,
        environment_type: environmentType,
        equipment_tags: equipmentTags,
        is_default: isDefault,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Not a <form> — this component is used inside OnboardingPage's own
    // <form>, and nested forms are invalid HTML / break submit semantics.
    <div className="space-y-4">
      <FormField
        label="Name"
        name="name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="e.g., My Home Gym"
        required
      />

      <div className="input-group">
        <label htmlFor="environment_type" className="input-label">
          Type <span className="text-error-600">*</span>
        </label>
        <select
          id="environment_type"
          name="environment_type"
          value={environmentType}
          onChange={(e) => handleEnvironmentTypeChange(e.target.value as typeof environmentType)}
          required
        >
          {ENVIRONMENT_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <EquipmentPicker
        selected={equipmentTags}
        onChange={setEquipmentTags}
        environmentType={environmentType}
      />

      <label className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50 border-t border-neutral-200 dark:border-neutral-700 pt-4">
        <input
          type="checkbox"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.target.checked)}
        />
        Set as default environment
      </label>

      <div className="flex gap-3 pt-2">
        <Button
          type="button"
          variant="primary"
          isLoading={submitting}
          onClick={handleSubmit}
          className="flex-1"
        >
          {submitLabel}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={submitting}
          className="flex-1"
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}
