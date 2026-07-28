// Kept in sync with backend/app/models/checkin.py and app/schemas/checkin.py

import type { InjuryRegion } from '@/types/injury';
import type { InjuryRecordPayload } from '@/types/injury';
import type { Advisory } from '@/types/program';

export type CheckInStatus = 'green' | 'amber' | 'red';

export const CHECK_IN_STATUS_OPTIONS: {
  value: CheckInStatus;
  label: string;
  emoji: string;
  className: string;
}[] = [
  {
    value: 'green',
    label: 'Feeling good',
    emoji: '🟢',
    className:
      'bg-green-100 text-green-900 hover:bg-green-200 dark:bg-green-900/40 dark:text-green-100 dark:hover:bg-green-900/60',
  },
  {
    value: 'amber',
    label: 'Some discomfort',
    emoji: '🟡',
    className:
      'bg-amber-100 text-amber-900 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-100 dark:hover:bg-amber-900/60',
  },
  {
    value: 'red',
    label: 'Sharp / concerning pain',
    emoji: '🔴',
    className:
      'bg-red-100 text-red-900 hover:bg-red-200 dark:bg-red-900/40 dark:text-red-100 dark:hover:bg-red-900/60',
  },
];

export interface CheckInPayload {
  region: InjuryRegion;
  status: CheckInStatus;
  note?: string;
}

export interface CheckIn {
  id: number;
  region: InjuryRegion;
  status: CheckInStatus;
  note: string | null;
  created_at: string;
}

export interface CheckInResult {
  check_in: CheckIn;
  excluded: boolean;
  consult_recommended: boolean;
  draft_injury_record: InjuryRecordPayload | null;
  advisories: Advisory[];
}
