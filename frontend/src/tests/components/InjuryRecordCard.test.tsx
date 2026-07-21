import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InjuryRecordCard } from '@/components';
import type { InjuryRecord } from '@/types/injury';

const injury: InjuryRecord = {
  id: 1,
  region: 'shoulder',
  condition: 'tendinopathy',
  phase: 'rehabilitating',
  provocations: ['overhead'],
  severity: 2,
  reported_at: '2026-01-15',
  source: 'user_reported',
};

describe('InjuryRecordCard', () => {
  it('should render human-readable labels for region, condition, phase, severity, and provocations', () => {
    render(<InjuryRecordCard injury={injury} />);

    expect(screen.getByText('Shoulder')).toBeInTheDocument();
    expect(screen.getByText('Tendinopathy')).toBeInTheDocument();
    expect(screen.getByText('Rehabilitating')).toBeInTheDocument();
    expect(screen.getByText('Moderate - limits some exercises')).toBeInTheDocument();
    expect(screen.getByText('Overhead movements')).toBeInTheDocument();
    expect(screen.getByText('Reported 2026-01-15')).toBeInTheDocument();
  });

  it('should call onDelete when Remove is clicked', () => {
    const onDelete = vi.fn();
    render(<InjuryRecordCard injury={injury} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: /Remove/i }));

    expect(onDelete).toHaveBeenCalled();
  });

  it('should hide the Remove button when onDelete is not provided', () => {
    render(<InjuryRecordCard injury={injury} />);

    expect(screen.queryByRole('button', { name: /Remove/i })).not.toBeInTheDocument();
  });
});
