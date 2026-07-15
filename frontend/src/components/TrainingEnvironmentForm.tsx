import { useState } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import { ENVIRONMENT_TYPE_OPTIONS, EQUIPMENT_TAG_OPTIONS } from '@/types/trainingEnvironment';
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

  const toggleTag = (tag: string) => {
    setEquipmentTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
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
          onChange={(e) => setEnvironmentType(e.target.value as typeof environmentType)}
          required
        >
          {ENVIRONMENT_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <span className="input-label block mb-2">Available Equipment</span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {EQUIPMENT_TAG_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={equipmentTags.includes(option.value)}
                onChange={() => toggleTag(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
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
