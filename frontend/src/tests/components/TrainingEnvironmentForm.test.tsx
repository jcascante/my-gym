import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TrainingEnvironmentForm } from '@/components';

describe('TrainingEnvironmentForm', () => {
  it('should submit the entered name, type, and manually selected tags for an unpreset archetype', async () => {
    const onSubmit = vi.fn();
    render(<TrainingEnvironmentForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'My Gym' } });
    fireEvent.change(screen.getByLabelText(/Type/), { target: { value: 'other' } });
    fireEvent.click(screen.getByLabelText('Dumbbells'));

    fireEvent.click(screen.getByRole('button', { name: /Save Environment/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'My Gym',
        environment_type: 'other',
        equipment_tags: ['dumbbells'],
        is_default: false,
      });
    });
  });

  it('should prefill equipment with the archetype preset when a type is selected', () => {
    render(<TrainingEnvironmentForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/Type/), { target: { value: 'powerlifting_gym' } });

    expect(screen.getByLabelText('Barbell')).toBeChecked();
    expect(screen.getByLabelText('Squat Rack')).toBeChecked();
    expect(screen.getByLabelText('Bench')).toBeChecked();
  });

  it('should narrow the visible equipment to the archetype preset by default', () => {
    render(<TrainingEnvironmentForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/Type/), { target: { value: 'powerlifting_gym' } });

    expect(screen.queryByLabelText('Leg Press')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Show all equipment/i }));
    expect(screen.getByLabelText('Leg Press')).toBeInTheDocument();
  });

  it('should pre-fill fields from initialValues for editing, keeping custom tags visible', () => {
    render(
      <TrainingEnvironmentForm
        initialValues={{
          name: 'Existing Gym',
          environment_type: 'home',
          equipment_tags: ['barbell'],
          is_default: true,
        }}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        submitLabel="Save Changes"
      />,
    );

    expect(screen.getByLabelText(/Name/)).toHaveValue('Existing Gym');
    expect(screen.getByLabelText('Barbell')).toBeChecked();
    expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
  });

  it('should call onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(<TrainingEnvironmentForm onSubmit={vi.fn()} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

    expect(onCancel).toHaveBeenCalled();
  });

  it('should not render a nested <form> element', () => {
    const { container } = render(<TrainingEnvironmentForm onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(container.querySelector('form')).toBeNull();
  });
});
