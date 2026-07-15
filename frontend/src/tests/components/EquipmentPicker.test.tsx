import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EquipmentPicker } from '@/components';

describe('EquipmentPicker', () => {
  it('should narrow visible options to the archetype preset by default', () => {
    render(<EquipmentPicker selected={[]} onChange={vi.fn()} environmentType="powerlifting_gym" />);

    expect(screen.getByLabelText('Barbell')).toBeInTheDocument();
    expect(screen.getByLabelText('Squat Rack')).toBeInTheDocument();
    expect(screen.queryByLabelText('Leg Press')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Kettlebell')).not.toBeInTheDocument();
  });

  it('should reveal the full catalog when "Show all equipment" is toggled', () => {
    render(<EquipmentPicker selected={[]} onChange={vi.fn()} environmentType="powerlifting_gym" />);

    fireEvent.click(screen.getByRole('button', { name: /Show all equipment/i }));

    expect(screen.getByLabelText('Leg Press')).toBeInTheDocument();
    expect(screen.getByLabelText('Kettlebell')).toBeInTheDocument();
  });

  it('should not narrow when the archetype has an empty preset', () => {
    render(<EquipmentPicker selected={[]} onChange={vi.fn()} environmentType="other" />);

    expect(screen.getByLabelText('Leg Press')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Show all equipment/i })).not.toBeInTheDocument();
  });

  it('should keep an already-selected tag visible even outside the preset', () => {
    render(
      <EquipmentPicker
        selected={['leg_press_machine']}
        onChange={vi.fn()}
        environmentType="powerlifting_gym"
      />,
    );

    expect(screen.getByLabelText('Leg Press')).toBeChecked();
  });

  it('should toggle a tag on click', () => {
    const onChange = vi.fn();
    render(
      <EquipmentPicker
        selected={['barbell']}
        onChange={onChange}
        environmentType="powerlifting_gym"
      />,
    );

    fireEvent.click(screen.getByLabelText('Squat Rack'));
    expect(onChange).toHaveBeenCalledWith(['barbell', 'squat_rack']);

    fireEvent.click(screen.getByLabelText('Barbell'));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
