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

    fireEvent.click(screen.getByRole('button', { name: /Generate Program/i }));

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
});
