import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProgramCreationForm } from '@/components';

describe('ProgramCreationForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should invoke onSubmit callback with collected values', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.change(screen.getByLabelText(/Days per Week/i), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText(/Session Duration/i), {
      target: { value: '45' },
    });

    const weightUnitSelect = screen.getByLabelText(/Weight Unit/i);
    fireEvent.change(weightUnitSelect, { target: { value: 'lbs' } });

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment_id: 1,
          days_per_week: 4,
          session_duration_min: 45,
          weight_unit: 'lbs',
        }),
      );
    });
  });

  it('should call onCancel when Cancel is clicked', () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

    expect(onCancel).toHaveBeenCalled();
  });

  it('should render as a controlled form with required fields', () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    expect(screen.getByLabelText(/Days per Week/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Session Duration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Weight Unit/i)).toBeInTheDocument();
  });

  it('should pre-fill form fields from initialValues', () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const initialValues = {
      environment_id: 1,
      days_per_week: 5,
      session_duration_min: 90,
      weight_unit: 'lbs' as const,
      progression_style: 'consistent' as const,
      effort_method: '' as const,
    };

    render(
      <ProgramCreationForm
        environmentId={1}
        onSubmit={onSubmit}
        onCancel={onCancel}
        initialValues={initialValues}
      />,
    );

    const daysInput = screen.getByLabelText(/Days per Week/i);
    const durationInput = screen.getByLabelText(/Session Duration/i);
    const weightSelect = screen.getByLabelText(/Weight Unit/i);

    expect(daysInput).toHaveValue(5);
    expect(durationInput).toHaveValue(90);
    expect(weightSelect).toHaveValue('lbs');
  });

  it('should include progression_style in submitted values, defaulting to consistent', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ progression_style: 'consistent' }),
      );
    });
  });

  it('should submit variable progression style when selected', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.change(screen.getByLabelText(/Progression Style/i), {
      target: { value: 'variable' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ progression_style: 'variable' }),
      );
    });
  });

  it('should update form fields when initialValues prop changes', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const initialValues1 = {
      environment_id: 1,
      days_per_week: 3,
      session_duration_min: 60,
      weight_unit: 'kg' as const,
      progression_style: 'consistent' as const,
      effort_method: '' as const,
    };

    const { rerender } = render(
      <ProgramCreationForm
        environmentId={1}
        onSubmit={onSubmit}
        onCancel={onCancel}
        initialValues={initialValues1}
      />,
    );

    expect(screen.getByLabelText(/Days per Week/i)).toHaveValue(3);

    const initialValues2 = {
      environment_id: 1,
      days_per_week: 6,
      session_duration_min: 120,
      weight_unit: 'lbs' as const,
      progression_style: 'consistent' as const,
      effort_method: '' as const,
    };

    rerender(
      <ProgramCreationForm
        environmentId={1}
        onSubmit={onSubmit}
        onCancel={onCancel}
        initialValues={initialValues2}
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/Days per Week/i)).toHaveValue(6);
      expect(screen.getByLabelText(/Session Duration/i)).toHaveValue(120);
      expect(screen.getByLabelText(/Weight Unit/i)).toHaveValue('lbs');
    });
  });

  it('should default effort_method to empty (no preference) and submit a chosen method', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.change(screen.getByLabelText(/Effort Tracking/i), {
      target: { value: 'rpe' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ effort_method: 'rpe' }));
    });
  });
});
