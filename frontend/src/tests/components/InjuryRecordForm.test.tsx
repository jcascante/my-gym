import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { InjuryRecordForm } from '@/components';

describe('InjuryRecordForm', () => {
  it('should submit the selected region, condition, phase, severity, source, date, and provocations', async () => {
    const onSubmit = vi.fn();
    render(<InjuryRecordForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/Body Region/), { target: { value: 'knee' } });
    fireEvent.change(screen.getByLabelText(/Condition/), { target: { value: 'tendinopathy' } });
    fireEvent.change(screen.getByLabelText(/Recovery Phase/), {
      target: { value: 'rehabilitating' },
    });
    fireEvent.change(screen.getByLabelText(/Severity/), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText(/Reported By/), {
      target: { value: 'professional_cleared' },
    });
    fireEvent.change(screen.getByLabelText(/Date/), { target: { value: '2026-01-15' } });
    fireEvent.click(screen.getByLabelText('Deep knee bend'));

    fireEvent.click(screen.getByRole('button', { name: /Add Injury/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        region: 'knee',
        condition: 'tendinopathy',
        phase: 'rehabilitating',
        source: 'professional_cleared',
        severity: 2,
        reported_at: '2026-01-15',
        provocations: ['deep_knee_flexion'],
      });
    });
  });

  it('should default to today, mild severity, and no provocations', async () => {
    const onSubmit = vi.fn();
    render(<InjuryRecordForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Add Injury/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 1,
          provocations: [],
          reported_at: new Date().toISOString().slice(0, 10),
        }),
      );
    });
  });

  it('should call onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(<InjuryRecordForm onSubmit={vi.fn()} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

    expect(onCancel).toHaveBeenCalled();
  });

  it('should not render a nested <form> element', () => {
    const { container } = render(<InjuryRecordForm onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(container.querySelector('form')).toBeNull();
  });
});
