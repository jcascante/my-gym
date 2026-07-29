import { it, expect, describe } from 'vitest';
import { formatEffortDisplay } from '@/utils/effortDisplay';
import type { EffortTarget } from '@/types/program';

describe('formatEffortDisplay', () => {
  it('formats weight-based effort (lbs)', () => {
    const result = formatEffortDisplay(4, 10, 80, 'lbs', null);
    expect(result).toBe('4 x 10 @80 lbs');
  });

  it('formats weight-based effort (kg)', () => {
    const result = formatEffortDisplay(4, 10, 80, 'kg', null);
    expect(result).toBe('4 x 10 @80 kg');
  });

  it('formats percent_1rm effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'percent_1rm', pct: 0.7 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @70%');
  });

  it('formats RIR effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'rir', value: 1 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @RIR 1');
  });

  it('formats RPE effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 7 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @RPE 7');
  });

  it('formats Borg effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'borg', value: 12 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @Borg 12');
  });

  it('prefers weight over effort_target when both available', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 7 };
    const result = formatEffortDisplay(4, 10, 80, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @80 lbs');
  });

  it('returns sets x reps only when no weight and no effort_target', () => {
    const result = formatEffortDisplay(4, 10, null, 'lbs', null);
    expect(result).toBe('4 x 10');
  });

  it('handles decimal weight values', () => {
    const result = formatEffortDisplay(4, 10, 80.5, 'lbs', null);
    expect(result).toBe('4 x 10 @80.5 lbs');
  });
});
