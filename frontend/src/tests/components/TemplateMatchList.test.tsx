import { it, expect, vi, describe } from 'vitest';
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
    tier: 'best' as const,
    all_infeasible: false,
  },
  {
    template_id: 2,
    slug: 'fb',
    name: 'Full Body x3',
    fit_pct: 85,
    factors: { goal: 1 },
    required_inputs: [],
    tier: 'strong' as const,
    all_infeasible: false,
  },
];

const matchesInfeasible = [
  {
    template_id: 1,
    slug: 'ul',
    name: 'Upper/Lower x4',
    fit_pct: 60,
    factors: { goal: 0.6 },
    required_inputs: [],
    tier: 'possible' as const,
    all_infeasible: true,
  },
];

describe('TemplateMatchList', () => {
  it('renders tier badge with correct copy for "best"', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('Best match')).toBeInTheDocument();
  });

  it('renders tier badge with correct copy for "strong"', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('Strong fit')).toBeInTheDocument();
  });

  it('renders fit % for power users (demoted)', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText(/Fit: 92%/)).toBeInTheDocument();
  });

  it('selects on click', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button', { name: /Upper\/Lower x4/ }));
    expect(onSelect).toHaveBeenCalledWith(matches[0]);
  });

  it('shows all-infeasible warning when all_infeasible is true', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matchesInfeasible} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('No perfect match found')).toBeInTheDocument();
    expect(
      screen.getByText(/None of your available templates fully match your setup/),
    ).toBeInTheDocument();
  });

  it('does not show all-infeasible warning when all_infeasible is false', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.queryByText('No perfect match found')).not.toBeInTheDocument();
  });

  it('renders empty state when no matches', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={[]} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('No matching templates for your setup.')).toBeInTheDocument();
  });
});
