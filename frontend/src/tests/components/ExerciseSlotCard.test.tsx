import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExerciseSlotCard } from '@/components/ExerciseSlotCard';
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
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
  rotation_pool: [],
  tempo: 'controlled',
  warmup_sets: [],
};

describe('ExerciseSlotCard', () => {
  describe('rest_seconds rendering', () => {
    it('formats rest seconds less than 60 as "Xs"', () => {
      const slot = { ...baseSlot, rest_seconds: 45 };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Rest: 45s/)).toBeInTheDocument();
    });

    it('formats rest seconds as exact minute when divisible by 60', () => {
      const slot = { ...baseSlot, rest_seconds: 120 };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Rest: 2m/)).toBeInTheDocument();
    });

    it('formats rest seconds as "Xm Ys" when greater than 60 with remainder', () => {
      const slot = { ...baseSlot, rest_seconds: 68 };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Rest: 1m 8s/)).toBeInTheDocument();
    });

    it('formats rest seconds as "Xm" when exactly 60 seconds', () => {
      const slot = { ...baseSlot, rest_seconds: 60 };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Rest: 1m/)).toBeInTheDocument();
    });
  });

  describe('tempo rendering', () => {
    it('does not render tempo tag when tempo is "controlled"', () => {
      const slot = { ...baseSlot, tempo: 'controlled' };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.queryByText(/Tempo:/)).not.toBeInTheDocument();
    });

    it('renders tempo tag when tempo is not "controlled"', () => {
      const slot = { ...baseSlot, tempo: 'eccentric_2s' };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Tempo: eccentric_2s/)).toBeInTheDocument();
    });
  });

  describe('warmup_sets rendering', () => {
    it('does not render warmup block when warmup_sets is empty', () => {
      const slot = { ...baseSlot, warmup_sets: [] };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.queryByText(/Warm-up:/)).not.toBeInTheDocument();
    });

    it('renders warmup block with correct format for single warmup set', () => {
      const slot = {
        ...baseSlot,
        warmup_sets: [{ pct: 0.5, reps: 5, load: 50 }],
      };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Warm-up: 50%×5/)).toBeInTheDocument();
    });

    it('renders warmup block with correct format for multiple warmup sets', () => {
      const slot = {
        ...baseSlot,
        warmup_sets: [
          { pct: 0.4, reps: 5, load: 48 },
          { pct: 0.6, reps: 3, load: 72 },
          { pct: 0.8, reps: 1, load: 96 },
        ],
      };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Warm-up: 40%×5, 60%×3, 80%×1/)).toBeInTheDocument();
    });

    it('handles warmup sets with null load values', () => {
      const slot = {
        ...baseSlot,
        warmup_sets: [
          { pct: 0.4, reps: 5, load: null },
          { pct: 0.6, reps: 3, load: null },
        ],
      };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Warm-up: 40%×5, 60%×3/)).toBeInTheDocument();
    });
  });

  describe('integration', () => {
    it('renders rest, tempo, and warmup together when all are present', () => {
      const slot = {
        ...baseSlot,
        rest_seconds: 180,
        tempo: 'explosive_1s',
        warmup_sets: [
          { pct: 0.5, reps: 5, load: 50 },
          { pct: 0.75, reps: 2, load: 75 },
        ],
      };
      render(<ExerciseSlotCard slot={slot} readOnly />);
      expect(screen.getByText(/Rest: 3m/)).toBeInTheDocument();
      expect(screen.getByText(/Tempo: explosive_1s/)).toBeInTheDocument();
      expect(screen.getByText(/Warm-up: 50%×5, 75%×2/)).toBeInTheDocument();
    });

    it('renders exercise name and basic info', () => {
      render(<ExerciseSlotCard slot={baseSlot} readOnly />);
      expect(screen.getByText('Barbell Back Squat')).toBeInTheDocument();
      expect(screen.getByText(/3×5/)).toBeInTheDocument();
    });

    it('can be rendered with onAction and onSwap callbacks', () => {
      const onAction = vi.fn();
      const onSwap = vi.fn();
      render(<ExerciseSlotCard slot={baseSlot} onAction={onAction} onSwap={onSwap} />);
      expect(screen.getByText('Barbell Back Squat')).toBeInTheDocument();
    });
  });
});
