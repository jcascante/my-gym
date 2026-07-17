import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { SkeletonLoader } from '@/components';

describe('SkeletonLoader', () => {
  it('renders default number of skeleton lines', () => {
    const { container } = render(<SkeletonLoader />);
    const lines = container.querySelectorAll('.h-6');
    expect(lines.length).toBe(3);
  });

  it('renders custom number of skeleton lines', () => {
    const { container } = render(<SkeletonLoader lines={5} />);
    const lines = container.querySelectorAll('div');
    expect(lines.length).toBeGreaterThanOrEqual(5);
  });

  it('renders with small height', () => {
    const { container } = render(<SkeletonLoader height="sm" />);
    const line = container.querySelector('.h-4');
    expect(line).toBeInTheDocument();
  });

  it('renders with large height', () => {
    const { container } = render(<SkeletonLoader height="lg" />);
    const line = container.querySelector('.h-8');
    expect(line).toBeInTheDocument();
  });

  it('has pulse animation', () => {
    const { container } = render(<SkeletonLoader />);
    const lines = container.querySelectorAll('.animate-pulse');
    expect(lines.length).toBe(3);
  });
});
