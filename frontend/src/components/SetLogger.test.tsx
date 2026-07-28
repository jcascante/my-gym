import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SetLogger } from './SetLogger';

describe('SetLogger', () => {
  const mockOnSetLogged = vi.fn();

  beforeEach(() => {
    mockOnSetLogged.mockClear();
  });

  it('renders weight, reps, and RPE inputs', () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    expect(screen.getByLabelText(/weight/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reps/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rpe/i)).toBeInTheDocument();
  });

  it('clamps RPE to 1–10 range', () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    const rpeInput = screen.getByLabelText(/rpe/i);
    fireEvent.change(rpeInput, { target: { value: '15' } });
    fireEvent.blur(rpeInput);
    expect((rpeInput as HTMLInputElement).value).toBe('10');
  });

  it('clamps RIR to 0–10 range', () => {
    render(<SetLogger effort_method="rir" onSetLogged={mockOnSetLogged} />);
    const rirInput = screen.getByLabelText(/reps in reserve/i);
    fireEvent.change(rirInput, { target: { value: '-5' } });
    fireEvent.blur(rirInput);
    expect((rirInput as HTMLInputElement).value).toBe('0');
  });

  it('clamps Borg scale to 6–20', () => {
    render(<SetLogger effort_method="borg" onSetLogged={mockOnSetLogged} />);
    const borgInput = screen.getByLabelText(/perceived exertion/i);
    fireEvent.change(borgInput, { target: { value: '25' } });
    fireEvent.blur(borgInput);
    expect((borgInput as HTMLInputElement).value).toBe('20');
  });

  it('rejects negative weight', () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    const weightInput = screen.getByLabelText(/weight/i);
    fireEvent.change(weightInput, { target: { value: '-10' } });
    fireEvent.blur(weightInput);
    expect((weightInput as HTMLInputElement).value).toBe('');
  });

  it('rejects reps < 1 or > 100', () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    const repsInput = screen.getByLabelText(/reps/i);
    fireEvent.change(repsInput, { target: { value: '101' } });
    fireEvent.blur(repsInput);
    expect((repsInput as HTMLInputElement).value).toBe('');
  });

  it('calls onSetLogged with valid input on submit', async () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    const weightInput = screen.getByLabelText(/weight/i);
    const repsInput = screen.getByLabelText(/reps/i);
    const rpeInput = screen.getByLabelText(/rpe/i);
    const submitBtn = screen.getByRole('button', { name: /log set/i });

    fireEvent.change(weightInput, { target: { value: '185' } });
    fireEvent.change(repsInput, { target: { value: '8' } });
    fireEvent.change(rpeInput, { target: { value: '8.5' } });
    fireEvent.click(submitBtn);

    expect(mockOnSetLogged).toHaveBeenCalledWith({
      weight: 185,
      reps: 8,
      effort: 8.5,
      effort_method: 'rpe',
    });

    await waitFor(() => expect((submitBtn as HTMLButtonElement).disabled).toBe(true));
  });

  it('resets form after submit', async () => {
    render(<SetLogger effort_method="rpe" onSetLogged={mockOnSetLogged} />);
    const weightInput = screen.getByLabelText(/weight/i);
    const repsInput = screen.getByLabelText(/reps/i);
    const rpeInput = screen.getByLabelText(/rpe/i);
    const submitBtn = screen.getByRole('button', { name: /log set/i });

    fireEvent.change(weightInput, { target: { value: '185' } });
    fireEvent.change(repsInput, { target: { value: '8' } });
    fireEvent.change(rpeInput, { target: { value: '8.5' } });
    fireEvent.click(submitBtn);

    await waitFor(() => expect((weightInput as HTMLInputElement).value).toBe(''));
    expect((repsInput as HTMLInputElement).value).toBe('');
    expect((rpeInput as HTMLInputElement).value).toBe('');
  });

  it('disables the submit button while a log request is in flight', async () => {
    let resolveLog: () => void = () => {};
    const pending = new Promise<void>((resolve) => {
      resolveLog = resolve;
    });
    const slowOnSetLogged = vi.fn().mockReturnValue(pending);
    render(<SetLogger effort_method="rpe" onSetLogged={slowOnSetLogged} />);
    const rpeInput = screen.getByLabelText(/rpe/i);
    const submitBtn = screen.getByRole('button', { name: /log set/i });

    fireEvent.change(rpeInput, { target: { value: '8' } });
    fireEvent.click(submitBtn);

    await waitFor(() => expect((submitBtn as HTMLButtonElement).disabled).toBe(true));
    expect(slowOnSetLogged).toHaveBeenCalledTimes(1);

    resolveLog();
    await waitFor(() => expect(slowOnSetLogged).toHaveBeenCalledTimes(1));
    fireEvent.change(rpeInput, { target: { value: '8' } });
    await waitFor(() => expect((submitBtn as HTMLButtonElement).disabled).toBe(false));
  });
});
