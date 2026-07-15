import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProgramCreationForm } from '@/components';
import { createProgram } from '@/api/programs';

vi.mock('@/api/programs');

describe('ProgramCreationForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show a coming-soon message after a 501 response', async () => {
    vi.mocked(createProgram).mockRejectedValue({ response: { status: 501 } });

    render(<ProgramCreationForm environmentId={1} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Generate Program/i }));

    await waitFor(() => {
      expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
    });
  });

  it('should submit the full preferences payload', async () => {
    vi.mocked(createProgram).mockRejectedValue({ response: { status: 501 } });

    render(<ProgramCreationForm environmentId={7} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByLabelText('Monday'));
    fireEvent.click(screen.getByLabelText('Push (chest, shoulders, triceps)'));
    fireEvent.click(screen.getByRole('button', { name: /Generate Program/i }));

    await waitFor(() => {
      expect(createProgram).toHaveBeenCalledWith(
        expect.objectContaining({
          environment_id: 7,
          preferred_days: ['monday'],
          focus_areas: ['push'],
          weight_unit: 'kg',
          progression_style: 'consistent',
        }),
      );
    });
  });

  it('should show a generic error message on unexpected failures', async () => {
    vi.mocked(createProgram).mockRejectedValue(new Error('boom'));

    render(<ProgramCreationForm environmentId={1} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Generate Program/i }));

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  it('should call onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(<ProgramCreationForm environmentId={1} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

    expect(onCancel).toHaveBeenCalled();
  });
});
