import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TemplateListItem from '@/components/TemplateListItem';
import type { Template } from '@/types/template';

const mockTemplate: Template = {
  slug: 'full-body-x3',
  name: 'Full Body 3x/Week',
  description: 'Three full-body days for beginners building general strength.',
  goals: ['general', 'strength'],
  experience_levels: ['beginner'],
  days_per_week_min: 3,
  days_per_week_max: 3,
  session_duration_min: 45,
  session_duration_max: 60,
  split: {
    sessions: [
      {
        key: 'full_a',
        name: 'Full Body A',
        order: 1,
        slots: [
          { pattern: 'squat', priority: 'primary', scheme: 'main' },
          { pattern: 'horizontal_push', priority: 'primary', scheme: 'main' },
        ],
      },
    ],
    schemes: {
      main: {
        sets: 3,
        reps_min: 5,
        reps_max: 5,
        rest_seconds: 120,
        target_rpe: 8.0,
        intensity_pct: 0.8,
      },
      accessory: {
        sets: 4,
        reps_min: 10,
        reps_max: 12,
        rest_seconds: 60,
        target_rpe: 7.0,
        intensity_pct: 0.65,
      },
    },
  },
  progression_ref: { model_key: 'linear_load', params: { increment: 2.5 }, deload_every: 4 },
  required_inputs: [
    { key: 'squat_start', label: 'Comfortable squat weight', type: 'number', applies_to: 'squat' },
  ],
};

describe('TemplateListItem', () => {
  it('should render compact row with template name and summary', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={false} onToggle={() => {}} />);

    expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    expect(screen.getByText(/beginner/i)).toBeInTheDocument();
    expect(screen.getByText(/general/i)).toBeInTheDocument();
    expect(screen.getByText(/3 days/i)).toBeInTheDocument();
    expect(screen.getByText(/45-60/i)).toBeInTheDocument();
  });

  it('should show right chevron when collapsed', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={false} onToggle={() => {}} />);

    const chevron = screen.getByText('▶');
    expect(chevron).toBeInTheDocument();
  });

  it('should show down chevron when expanded', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={true} onToggle={() => {}} />);

    const chevron = screen.getByText('▼');
    expect(chevron).toBeInTheDocument();
  });

  it('should call onToggle when row is clicked', () => {
    const onToggle = vi.fn();
    render(<TemplateListItem template={mockTemplate} isExpanded={false} onToggle={onToggle} />);

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('should render expanded details when isExpanded is true', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={true} onToggle={() => {}} />);

    expect(
      screen.getByText('Three full-body days for beginners building general strength.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Full Body A')).toBeInTheDocument();
    expect(screen.getByText('linear_load')).toBeInTheDocument();
  });

  it('should display set/rep schemes in expanded view', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={true} onToggle={() => {}} />);

    expect(screen.getByText('main')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // sets
    expect(screen.getByText('5')).toBeInTheDocument(); // reps
    expect(screen.getByText('120')).toBeInTheDocument(); // rest seconds
  });

  it('should display required inputs when present', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={true} onToggle={() => {}} />);

    expect(screen.getByText('Comfortable squat weight')).toBeInTheDocument();
  });
});
