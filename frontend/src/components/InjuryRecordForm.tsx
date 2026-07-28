import { useState } from 'react';
import { Button } from './Button';
import {
  INJURY_REGION_OPTIONS,
  INJURY_CONDITION_OPTIONS,
  INJURY_PHASE_OPTIONS,
  INJURY_SOURCE_OPTIONS,
  PROVOCATION_OPTIONS,
  SEVERITY_OPTIONS,
} from '@/types/injury';
import type { InjuryRecordPayload, Provocation } from '@/types/injury';

interface InjuryRecordFormProps {
  onSubmit: (payload: InjuryRecordPayload) => void | Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function InjuryRecordForm({
  onSubmit,
  onCancel,
  submitLabel = 'Add Injury',
}: InjuryRecordFormProps) {
  const [region, setRegion] = useState(INJURY_REGION_OPTIONS[0].value);
  const [condition, setCondition] = useState(INJURY_CONDITION_OPTIONS[0].value);
  const [phase, setPhase] = useState(INJURY_PHASE_OPTIONS[0].value);
  const [source, setSource] = useState(INJURY_SOURCE_OPTIONS[0].value);
  const [severity, setSeverity] = useState(SEVERITY_OPTIONS[0].value);
  const [reportedAt, setReportedAt] = useState(todayIsoDate());
  const [provocations, setProvocations] = useState<Provocation[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const toggleProvocation = (tag: Provocation) => {
    setProvocations((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        region,
        condition,
        phase,
        source,
        severity,
        reported_at: reportedAt,
        provocations,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Not a <form> — used inside OnboardingPage's own <form>, and nested
    // forms are invalid HTML / break submit semantics.
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="input-group">
          <label htmlFor="injury_region" className="input-label">
            Body Region
          </label>
          <select
            id="injury_region"
            value={region}
            onChange={(e) => setRegion(e.target.value as typeof region)}
          >
            {INJURY_REGION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="injury_condition" className="input-label">
            Condition
          </label>
          <select
            id="injury_condition"
            value={condition}
            onChange={(e) => setCondition(e.target.value as typeof condition)}
          >
            {INJURY_CONDITION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="injury_phase" className="input-label">
            Recovery Phase
          </label>
          <select
            id="injury_phase"
            value={phase}
            onChange={(e) => setPhase(e.target.value as typeof phase)}
          >
            {INJURY_PHASE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="injury_severity" className="input-label">
            Severity
          </label>
          <select
            id="injury_severity"
            value={severity}
            onChange={(e) => setSeverity(Number(e.target.value))}
          >
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="injury_source" className="input-label">
            Reported By
          </label>
          <select
            id="injury_source"
            value={source}
            onChange={(e) => setSource(e.target.value as typeof source)}
          >
            {INJURY_SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label htmlFor="injury_reported_at" className="input-label">
            Date
          </label>
          <input
            id="injury_reported_at"
            type="date"
            value={reportedAt}
            onChange={(e) => setReportedAt(e.target.value)}
          />
        </div>
      </div>

      <div>
        <span className="input-label">What makes it worse? (optional)</span>
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {PROVOCATION_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={provocations.includes(option.value)}
                onChange={() => toggleProvocation(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

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
