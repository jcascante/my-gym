import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TrainingEnvironmentCard } from '@/components';
import type { TrainingEnvironment } from '@/types/trainingEnvironment';

const environment: TrainingEnvironment = {
  id: 1,
  name: 'Home Gym',
  environment_type: 'home',
  equipment_tags: ['dumbbells', 'pull_up_bar'],
  is_default: true,
};

function renderWithRouter(element: React.ReactElement) {
  return render(<BrowserRouter>{element}</BrowserRouter>);
}

describe('TrainingEnvironmentCard', () => {
  it('should render name, type, tags, and default badge', () => {
    renderWithRouter(<TrainingEnvironmentCard environment={environment} />);

    expect(screen.getByText('Home Gym')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Default')).toBeInTheDocument();
    expect(screen.getByText('Dumbbells')).toBeInTheDocument();
    expect(screen.getByText('Pull-up Bar')).toBeInTheDocument();
  });

  it('should call onEdit and onDelete when clicked', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    renderWithRouter(
      <TrainingEnvironmentCard environment={environment} onEdit={onEdit} onDelete={onDelete} />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));
    fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

    expect(onEdit).toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
  });

  it('should hide Edit/Delete when readOnly', () => {
    renderWithRouter(
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

  it('should link to /programs/new for Generate Program', () => {
    renderWithRouter(<TrainingEnvironmentCard environment={environment} />);

    const link = screen.getByRole('link', { name: /Generate Program/i });
    expect(link).toHaveAttribute('href', '/programs/new');
  });
});
