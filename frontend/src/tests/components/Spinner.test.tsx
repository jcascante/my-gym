import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Spinner } from '@/components';

describe('Spinner', () => {
  it('renders with default props', () => {
    const { container } = render(<Spinner />);
    const spinner = container.querySelector('.w-6.h-6');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with small size', () => {
    const { container } = render(<Spinner size="sm" />);
    const spinner = container.querySelector('.w-4.h-4');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with large size', () => {
    const { container } = render(<Spinner size="lg" />);
    const spinner = container.querySelector('.w-8.h-8');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with primary color', () => {
    const { container } = render(<Spinner color="primary" />);
    const spinner = container.querySelector('.text-primary-600');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with success color', () => {
    const { container } = render(<Spinner color="success" />);
    const spinner = container.querySelector('.text-success-600');
    expect(spinner).toBeInTheDocument();
  });

  it('renders SVG element', () => {
    const { container } = render(<Spinner />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
