import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TrainingEnvironmentCard } from '@/components';
import type { TrainingEnvironment } from '@/types/trainingEnvironment';

const environment: TrainingEnvironment = {
  id: 1,
  name: 'Home Gym',
  environment_type: 'home',
  equipment_tags: ['dumbbells', 'pull_up_bar'],
  is_default: true,
};

describe('TrainingEnvironmentCard', () => {
  it('should render name, type, tags, and default badge', () => {
    render(<TrainingEnvironmentCard environment={environment} />);

    expect(screen.getByText('Home Gym')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Default')).toBeInTheDocument();
    expect(screen.getByText('Dumbbells')).toBeInTheDocument();
    expect(screen.getByText('Pull-up Bar')).toBeInTheDocument();
  });

  it('should call onEdit and onDelete when clicked', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(
      <TrainingEnvironmentCard environment={environment} onEdit={onEdit} onDelete={onDelete} />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));
    fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

    expect(onEdit).toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
  });

  it('should hide Edit/Delete when readOnly', () => {
    render(
      <TrainingEnvironmentCard
        environment={environment}
        readOnly
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete/i })).not.toBeInTheDocument();
  });

  it('should call onGenerateProgram when the button is clicked', () => {
    const onGenerateProgram = vi.fn();
    render(
      <TrainingEnvironmentCard environment={environment} onGenerateProgram={onGenerateProgram} />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Generate Program/i }));

    expect(onGenerateProgram).toHaveBeenCalled();
  });
});
