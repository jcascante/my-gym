import { useState } from 'react';
import { Card } from './Card';
import { Button } from './Button';
import { Alert } from './Alert';
import { useCreateCheckIn, useCheckIns } from '@/hooks/useCheckIns';
import { useCreateInjuryRecord } from '@/hooks/useInjuries';
import { CHECK_IN_STATUS_OPTIONS } from '@/types/checkin';
import { INJURY_REGION_OPTIONS } from '@/types/injury';
import type { InjuryRegion, InjuryRecordPayload } from '@/types/injury';
import type { CheckInStatus } from '@/types/checkin';

function regionLabel(region: InjuryRegion): string {
  return INJURY_REGION_OPTIONS.find((option) => option.value === region)?.label ?? region;
}

function DraftInjuryConfirmation({ draft }: { draft: InjuryRecordPayload }) {
  const confirmInjury = useCreateInjuryRecord();

  if (confirmInjury.isSuccess) {
    return <p className="text-sm text-neutral-600 dark:text-neutral-400">Injury record saved.</p>;
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-3">
      <p className="text-sm text-neutral-700 dark:text-neutral-300">
        Confirm a new injury record for {regionLabel(draft.region)}?
      </p>
      <Button
        size="sm"
        variant="primary"
        isLoading={confirmInjury.isPending}
        onClick={() => confirmInjury.mutate(draft)}
      >
        Confirm
      </Button>
    </div>
  );
}

export function CheckInWidget({ programId }: { programId: number }) {
  const [region, setRegion] = useState<InjuryRegion | null>(null);
  const checkIn = useCreateCheckIn(programId);
  const recent = useCheckIns(programId);

  const handleStatus = (status: CheckInStatus) => {
    if (!region) return;
    checkIn.mutate({ region, status });
  };

  const reset = () => {
    setRegion(null);
    checkIn.reset();
  };

  return (
    <Card padding="md" className="space-y-4">
      <h3 className="font-semibold text-neutral-900 dark:text-neutral-50">How are you feeling?</h3>

      {checkIn.data ? (
        <div className="space-y-3">
          {checkIn.data.advisories.length > 0 ? (
            checkIn.data.advisories.map((advisory, i) => (
              <Alert key={i} type={advisory.severity}>
                {advisory.message}
              </Alert>
            ))
          ) : (
            <Alert type="success">
              Check-in saved for {regionLabel(checkIn.data.check_in.region)}.
            </Alert>
          )}
          {checkIn.data.draft_injury_record && (
            <DraftInjuryConfirmation draft={checkIn.data.draft_injury_record} />
          )}
          <Button variant="secondary" size="sm" onClick={reset}>
            Check in again
          </Button>
        </div>
      ) : region ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-neutral-600 dark:text-neutral-400">{regionLabel(region)}</p>
            <button
              onClick={() => setRegion(null)}
              className="text-sm text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
            >
              Change
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {CHECK_IN_STATUS_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleStatus(option.value)}
                disabled={checkIn.isPending}
                className={`rounded-lg py-4 text-sm font-semibold transition-colors disabled:opacity-50 ${option.className}`}
              >
                <span className="block text-2xl mb-1">{option.emoji}</span>
                {option.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {INJURY_REGION_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setRegion(option.value)}
              className="rounded-lg py-2 px-3 text-sm font-medium bg-neutral-100 text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-600 transition-colors"
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {recent.data && recent.data.length > 0 && (
        <div className="pt-2 border-t border-neutral-200 dark:border-neutral-700">
          <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-2">Recent check-ins</p>
          <div className="flex flex-wrap gap-2">
            {recent.data
              .slice(-5)
              .reverse()
              .map((c) => {
                const option = CHECK_IN_STATUS_OPTIONS.find((o) => o.value === c.status);
                return (
                  <span
                    key={c.id}
                    className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
                  >
                    {option?.emoji} {regionLabel(c.region)}
                  </span>
                );
              })}
          </div>
        </div>
      )}
    </Card>
  );
}
