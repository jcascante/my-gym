import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SlotRow } from '@/components/SlotRow';
import type { SlotPreview } from '@/types/program';

const baseSlot: SlotPreview = {
  workout_exercise_id: 1,
  exercise_id: 1,
  exercise_name: 'Barbell Back Squat',
  sets: 3,
  reps: 5,
  load: 100,
  rest_seconds: 120,
  note: null,
  adjustment_reason: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: 'controlled',
  warmup_sets: [],
};

describe('SlotRow', () => {
  it('renders plain sets x reps when load and effort_target are both null', () => {
    const slot = { ...baseSlot, load: null };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.queryByText(/RPE|RIR|Borg|%/)).not.toBeInTheDocument();
    expect(screen.getByText('3 x 5')).toBeInTheDocument();
  });

  it('shows the load with weight unit when present', () => {
    render(<SlotRow slot={baseSlot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('3 x 5 @100 kg')).toBeInTheDocument();
  });

  it('renders an RPE effort target when load is absent', () => {
    const slot = {
      ...baseSlot,
      load: null,
      effort_target: { method: 'rpe' as const, value: 8 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/RPE 8/i)).toBeInTheDocument();
  });

  it('renders a percent_1rm effort target as a percentage when load is absent', () => {
    const slot = {
      ...baseSlot,
      load: null,
      effort_target: { method: 'percent_1rm' as const, pct: 0.8, target_load: 80 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });

  it('renders an RIR effort target when load is absent', () => {
    const slot = {
      ...baseSlot,
      load: null,
      effort_target: { method: 'rir' as const, value: 5 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/RIR 5/i)).toBeInTheDocument();
  });

  it('renders a Borg effort target when load is absent', () => {
    const slot = {
      ...baseSlot,
      load: null,
      effort_target: { method: 'borg' as const, value: 13 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/Borg 13/i)).toBeInTheDocument();
  });

  it('shows rotation badge when rotation_pool has multiple exercises', () => {
    const slot = { ...baseSlot, rotation_pool: [1, 2, 3] };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/🔁 rotates weekly/)).toBeInTheDocument();
  });

  it('does not show rotation badge when rotation_pool has one or fewer exercises', () => {
    const slot = { ...baseSlot, rotation_pool: [1] };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.queryByText(/🔁 rotates weekly/)).not.toBeInTheDocument();
  });

  it('shows an effort suffix chip when load and effort_target are both present', () => {
    const slot = {
      ...baseSlot,
      load: 100,
      effort_target: { method: 'rpe' as const, value: 8 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('3 x 5 @100 kg')).toBeInTheDocument();
    expect(screen.getByText('RPE 8')).toBeInTheDocument();
  });

  it('does not show an effort suffix chip when load is present but effort_target is null', () => {
    render(<SlotRow slot={baseSlot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.queryByText(/RPE|RIR|Borg|%/)).not.toBeInTheDocument();
  });

  it('shows a friendly label for a deload note', () => {
    const slot = { ...baseSlot, note: 'deload' };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('Deload week')).toBeInTheDocument();
  });

  it('shows a friendly label for a ramp-capped note', () => {
    const slot = { ...baseSlot, note: 'ramp_capped' };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('Capped for safe progression')).toBeInTheDocument();
  });

  it('shows an unrecognized note as-is', () => {
    const slot = { ...baseSlot, note: 'Go heavy' };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('Go heavy')).toBeInTheDocument();
  });
});
