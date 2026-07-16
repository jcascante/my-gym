import { it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateMatchList } from '@/components/TemplateMatchList';

const matches = [
  {
    template_id: 1,
    slug: 'ul',
    name: 'Upper/Lower x4',
    fit_pct: 92,
    factors: { goal: 1 },
    required_inputs: [],
  },
  {
    template_id: 2,
    slug: 'fb',
    name: 'Full Body x3',
    fit_pct: 85,
    factors: { goal: 1 },
    required_inputs: [],
  },
];

it('renders fit % and selects on click', () => {
  const onSelect = vi.fn();
  render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
  expect(screen.getByText('92%')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Upper\/Lower x4/ }));
  expect(onSelect).toHaveBeenCalledWith(matches[0]);
});
