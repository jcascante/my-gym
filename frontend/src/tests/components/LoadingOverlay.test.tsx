import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingOverlay } from '@/components';

describe('LoadingOverlay', () => {
  it('renders when isVisible is true', () => {
    render(<LoadingOverlay isVisible={true} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('does not render when isVisible is false', () => {
    const { container } = render(<LoadingOverlay isVisible={false} />);
    expect(container.children.length).toBe(0);
  });

  it('displays custom message', () => {
    render(<LoadingOverlay isVisible={true} message="Loading workouts..." />);
    expect(screen.getByText('Loading workouts...')).toBeInTheDocument();
  });

  it('renders Spinner component inside', () => {
    const { container } = render(<LoadingOverlay isVisible={true} />);
    const spinner = container.querySelector('svg');
    expect(spinner).toBeInTheDocument();
  });

  it('has fixed positioning overlay', () => {
    const { container } = render(<LoadingOverlay isVisible={true} />);
    const overlay = container.firstChild;
    expect(overlay).toHaveClass('fixed', 'inset-0', 'z-50');
  });
});
