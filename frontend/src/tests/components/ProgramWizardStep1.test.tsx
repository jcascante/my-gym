import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgramWizardStep1 } from '@/components/ProgramWizardStep1';

describe('ProgramWizardStep1', () => {
  it('defaults the start date to today and submits it with the form values', () => {
    const onSubmit = vi.fn();
    const today = new Date().toISOString().slice(0, 10);

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    const startDateInput = screen.getByLabelText(/start date/i);
    expect((startDateInput as HTMLInputElement).value).toBe(today);

    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_date: today }));
  });

  it('submits a user-chosen start date', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/start date/i), { target: { value: '2026-08-10' } });
    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_date: '2026-08-10' }));
  });

  it('defaults program duration to 8 weeks and submits it with the form values', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    const durationInput = screen.getByLabelText(/program duration/i);
    expect((durationInput as HTMLInputElement).value).toBe('8');

    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ duration_weeks: 8 }));
  });

  it('submits a user-chosen program duration', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/program duration/i), { target: { value: '12' } });
    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ duration_weeks: 12 }));
  });
});
