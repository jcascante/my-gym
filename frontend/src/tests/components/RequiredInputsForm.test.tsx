import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RequiredInputsForm } from '@/components/RequiredInputsForm';

describe('RequiredInputsForm', () => {
  it('collects values and submits with coerced types', () => {
    const onSubmit = vi.fn();
    render(
      <RequiredInputsForm
        inputs={[
          { key: 'squat_start', label: 'Squat weight', type: 'number', applies_to: 'squat' },
        ]}
        onSubmit={onSubmit}
      />,
    );
    const input = screen.getByLabelText('Squat weight');
    fireEvent.change(input, { target: { value: '80' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(onSubmit).toHaveBeenCalledWith({ squat_start: 80 });
  });

  it('coerces text fields as strings', () => {
    const onSubmit = vi.fn();
    render(
      <RequiredInputsForm
        inputs={[{ key: 'focus', label: 'Training focus', type: 'text', applies_to: 'all' }]}
        onSubmit={onSubmit}
      />,
    );
    const input = screen.getByLabelText('Training focus');
    fireEvent.change(input, { target: { value: 'strength' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(onSubmit).toHaveBeenCalledWith({ focus: 'strength' });
  });

  it('handles multiple inputs', () => {
    const onSubmit = vi.fn();
    render(
      <RequiredInputsForm
        inputs={[
          { key: 'squat_start', label: 'Squat weight', type: 'number', applies_to: 'squat' },
          { key: 'goal', label: 'Your goal', type: 'text', applies_to: 'all' },
        ]}
        onSubmit={onSubmit}
      />,
    );
    const squat = screen.getByLabelText('Squat weight');
    const goal = screen.getByLabelText('Your goal');
    fireEvent.change(squat, { target: { value: '100' } });
    fireEvent.change(goal, { target: { value: 'strength' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(onSubmit).toHaveBeenCalledWith({ squat_start: 100, goal: 'strength' });
  });
});
