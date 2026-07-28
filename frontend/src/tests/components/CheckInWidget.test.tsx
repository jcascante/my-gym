import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CheckInWidget } from '@/components/CheckInWidget';
import type { CheckIn, CheckInPayload, CheckInResult } from '@/types/checkin';
import type { InjuryRecordPayload } from '@/types/injury';

interface MockCheckInMutation {
  data: CheckInResult | undefined;
  isPending: boolean;
  mutate: (payload: CheckInPayload) => void;
  reset: () => void;
}

interface MockInjuryMutation {
  isPending: boolean;
  isSuccess: boolean;
  mutate: (payload: InjuryRecordPayload) => void;
}

interface MockCheckInsQuery {
  data: CheckIn[];
}

const mutateCheckIn = vi.fn();
const mutateInjury = vi.fn();
let checkInState: MockCheckInMutation = {
  data: undefined,
  isPending: false,
  mutate: mutateCheckIn,
  reset: vi.fn(),
};
let injuryState: MockInjuryMutation = { isPending: false, isSuccess: false, mutate: mutateInjury };
let checkInsListState: MockCheckInsQuery = { data: [] };

vi.mock('@/hooks/useCheckIns', () => ({
  useCreateCheckIn: () => checkInState,
  useCheckIns: () => checkInsListState,
}));

vi.mock('@/hooks/useInjuries', () => ({
  useCreateInjuryRecord: () => injuryState,
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  checkInState = { data: undefined, isPending: false, mutate: mutateCheckIn, reset: vi.fn() };
  injuryState = { isPending: false, isSuccess: false, mutate: mutateInjury };
  checkInsListState = { data: [] };
});

it('starts on the region picker', () => {
  render(wrap(<CheckInWidget programId={1} />));
  expect(screen.getByText('Knee')).toBeInTheDocument();
  expect(screen.queryByText('Feeling good')).not.toBeInTheDocument();
});

it('shows the status taps after picking a region, and submits region + status on tap', () => {
  render(wrap(<CheckInWidget programId={1} />));
  fireEvent.click(screen.getByText('Knee'));

  expect(screen.getByText('Feeling good')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Some discomfort'));

  expect(mutateCheckIn).toHaveBeenCalledWith({ region: 'knee', status: 'amber' });
});

it('can go back to region picking via Change', () => {
  render(wrap(<CheckInWidget programId={1} />));
  fireEvent.click(screen.getByText('Knee'));
  fireEvent.click(screen.getByText('Change'));
  expect(screen.getByText('Shoulder')).toBeInTheDocument();
});

it('shows a success alert and no draft record for a green check-in with no advisories', () => {
  checkInState.data = {
    check_in: { id: 1, region: 'knee', status: 'green', note: null, created_at: '2026-01-01' },
    excluded: false,
    consult_recommended: false,
    draft_injury_record: null,
    advisories: [],
  };
  render(wrap(<CheckInWidget programId={1} />));
  expect(screen.getByText(/Check-in saved for Knee/)).toBeInTheDocument();
  expect(screen.getByText('Check in again')).toBeInTheDocument();
});

it('renders advisories and a draft-injury confirmation for a red check-in', () => {
  const draftInjuryRecord: InjuryRecordPayload = {
    region: 'shoulder',
    condition: 'acute_pain',
    phase: 'acute',
    provocations: [],
    severity: 3,
    reported_at: '2026-01-01',
    source: 'user_reported',
  };
  checkInState.data = {
    check_in: { id: 2, region: 'shoulder', status: 'red', note: null, created_at: '2026-01-01' },
    excluded: true,
    consult_recommended: true,
    draft_injury_record: draftInjuryRecord,
    advisories: [
      {
        code: 'CHECK_IN_RED_FLAG',
        severity: 'error',
        message: 'Red check-in for your shoulder.',
        subject: 'shoulder',
      },
    ],
  };
  render(wrap(<CheckInWidget programId={1} />));
  expect(screen.getByText('Red check-in for your shoulder.')).toBeInTheDocument();
  expect(screen.getByText(/Confirm a new injury record for Shoulder/)).toBeInTheDocument();

  fireEvent.click(screen.getByText('Confirm'));
  expect(mutateInjury).toHaveBeenCalledWith(draftInjuryRecord);
});

it('resets back to the region picker on "Check in again"', () => {
  checkInState.data = {
    check_in: { id: 1, region: 'knee', status: 'green', note: null, created_at: '2026-01-01' },
    excluded: false,
    consult_recommended: false,
    draft_injury_record: null,
    advisories: [],
  };
  render(wrap(<CheckInWidget programId={1} />));
  fireEvent.click(screen.getByText('Check in again'));
  expect(checkInState.reset).toHaveBeenCalled();
});

it('renders recent check-in history when present', () => {
  checkInsListState = {
    data: [{ id: 1, region: 'knee', status: 'green', note: null, created_at: '2026-01-01' }],
  };
  render(wrap(<CheckInWidget programId={1} />));
  expect(screen.getByText('Recent check-ins')).toBeInTheDocument();
  expect(screen.getByText(/🟢 Knee/)).toBeInTheDocument();
});

it('does not render recent check-in history when empty', () => {
  render(wrap(<CheckInWidget programId={1} />));
  expect(screen.queryByText('Recent check-ins')).not.toBeInTheDocument();
});
