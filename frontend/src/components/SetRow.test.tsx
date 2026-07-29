import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SetRow } from './SetRow';
import type { EffortMethod, WeightUnit } from '../types/programCreation';
import type { LoggedSetEntry } from '../hooks/useSessionProgress';

function SetRowHarness(props: {
  setNumber: number;
  effort_method: EffortMethod;
  weightUnit: WeightUnit;
  initialLoggedSet?: LoggedSetEntry;
}) {
  const [loggedSet, setLoggedSet] = useState(props.initialLoggedSet);
  const handleLogSet = (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => {
    setLoggedSet({ setNumber: props.setNumber, ...data, timestamp: new Date() });
  };
  return (
    <SetRow
      setNumber={props.setNumber}
      effort_method={props.effort_method}
      weightUnit={props.weightUnit}
      loggedSet={loggedSet}
      onLogSet={handleLogSet}
    />
  );
}

describe('SetRow', () => {
  it('renders an input row with a per-set Log button when unlogged', () => {
    render(<SetRow setNumber={2} effort_method="rpe" weightUnit="lbs" onLogSet={vi.fn()} />);

    expect(screen.getByText('Set 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Log Set 2' })).toBeInTheDocument();
  });

  it('calls onLogSet with the entered values and shows the logged summary after success', async () => {
    render(<SetRowHarness setNumber={1} effort_method="rpe" weightUnit="lbs" />);

    await userEvent.type(screen.getByLabelText(/weight/i), '185');
    await userEvent.type(screen.getByLabelText(/reps/i), '8');
    await userEvent.type(screen.getByLabelText(/rpe/i), '8.5');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    expect(
      await screen.findByRole('button', { name: /set 1 logged, tap to edit/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/set 1.*185 lb.*8 reps.*rpe 8\.5/i)).toBeInTheDocument();
  });

  it('tap-to-edit works for newly logged sets (no initial loggedSet prop)', async () => {
    render(<SetRowHarness setNumber={1} effort_method="rpe" weightUnit="lbs" />);

    // Log a new set
    await userEvent.type(screen.getByLabelText(/weight/i), '185');
    await userEvent.type(screen.getByLabelText(/reps/i), '8');
    await userEvent.type(screen.getByLabelText(/rpe/i), '8.5');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    expect(
      await screen.findByRole('button', { name: /set 1 logged, tap to edit/i }),
    ).toBeInTheDocument();

    // Tap the summary to edit
    await userEvent.click(screen.getByRole('button', { name: /set 1 logged, tap to edit/i }));

    // Inputs should be prefilled with the submitted values
    expect(screen.getByLabelText<HTMLInputElement>(/weight/i).value).toBe('185');
    expect(screen.getByLabelText<HTMLInputElement>(/reps/i).value).toBe('8');
    expect(screen.getByLabelText<HTMLInputElement>(/rpe/i).value).toBe('8.5');
  });

  it('renders a logged summary row when a loggedSet is passed in', () => {
    render(
      <SetRow
        setNumber={1}
        effort_method="rpe"
        weightUnit="lbs"
        loggedSet={{
          setNumber: 1,
          weight: 80,
          reps: 8,
          effort: 7,
          effort_method: 'rpe',
          timestamp: new Date(),
        }}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText(/set 1.*80 lb.*8 reps.*rpe 7/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Log Set 1' })).not.toBeInTheDocument();
  });

  it('tapping a logged summary reopens the input, prefilled, for correction', async () => {
    const onLogSet = vi.fn().mockResolvedValue(undefined);
    render(
      <SetRow
        setNumber={1}
        effort_method="rpe"
        weightUnit="lbs"
        loggedSet={{
          setNumber: 1,
          weight: 80,
          reps: 8,
          effort: 7,
          effort_method: 'rpe',
          timestamp: new Date(),
        }}
        onLogSet={onLogSet}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /set 1 logged, tap to edit/i }));

    expect(screen.getByLabelText<HTMLInputElement>(/weight/i).value).toBe('80');
    expect(screen.getByLabelText<HTMLInputElement>(/reps/i).value).toBe('8');
    expect(screen.getByLabelText<HTMLInputElement>(/rpe/i).value).toBe('7');
  });

  it('stays in the input state if onLogSet rejects', async () => {
    const onLogSet = vi.fn().mockRejectedValue(new Error('network error'));
    render(<SetRow setNumber={1} effort_method="rpe" weightUnit="lbs" onLogSet={onLogSet} />);

    await userEvent.type(screen.getByLabelText(/rpe/i), '8');
    await userEvent.click(screen.getByRole('button', { name: 'Log Set 1' }));

    await waitFor(() => expect(onLogSet).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Log Set 1' })).toBeInTheDocument();
  });

  it('clamps RPE to 1-10 range', async () => {
    render(<SetRow setNumber={1} effort_method="rpe" weightUnit="lbs" onLogSet={vi.fn()} />);
    const rpeInput = screen.getByLabelText(/rpe/i);
    await userEvent.type(rpeInput, '15');
    await userEvent.tab();
    expect((rpeInput as HTMLInputElement).value).toBe('10');
  });
});
