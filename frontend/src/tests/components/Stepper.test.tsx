import { it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Stepper } from '@/components/Stepper';

const STEPS = ['Preferences', 'Select', 'Details', 'Review'];

it('renders every step label with its position', () => {
  render(<Stepper steps={STEPS} current={0} />);
  expect(screen.getByText('1. Preferences')).toBeInTheDocument();
  expect(screen.getByText('2. Select')).toBeInTheDocument();
  expect(screen.getByText('3. Details')).toBeInTheDocument();
  expect(screen.getByText('4. Review')).toBeInTheDocument();
});

it('does not mark any step as skipped by default', () => {
  render(<Stepper steps={STEPS} current={3} />);
  expect(screen.queryByText(/\(skipped\)/)).not.toBeInTheDocument();
});

it('renders a skipped step with a distinct "(skipped)" label', () => {
  render(<Stepper steps={STEPS} current={3} skipped={[2]} />);
  expect(screen.getByText('3. Details (skipped)')).toBeInTheDocument();
  expect(screen.queryByText('3. Details')).not.toBeInTheDocument();
});

it('gives a skipped step an explanatory title for hover', () => {
  render(<Stepper steps={STEPS} current={3} skipped={[2]} />);
  expect(screen.getByText('3. Details (skipped)')).toHaveAttribute(
    'title',
    'Details: not needed for this template',
  );
});

it('only marks the steps listed in skipped, not others', () => {
  render(<Stepper steps={STEPS} current={3} skipped={[2]} />);
  expect(screen.getByText('1. Preferences')).not.toHaveAttribute('title');
  expect(screen.getByText('4. Review')).not.toHaveAttribute('title');
});
