import { it, expect, describe } from 'vitest';
import { formatEffortDisplay, formatEffortSuffix } from '@/utils/effortDisplay';
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
    expect(result).toBe('4 x 10 @70% 1RM');
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

describe('formatEffortSuffix', () => {
  it('returns null when there is no effort target', () => {
    expect(formatEffortSuffix(80, null)).toBeNull();
  });

  it('returns null when there is no load, even with an effort target', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 8 };
    expect(formatEffortSuffix(null, effortTarget)).toBeNull();
  });

  it('formats an RPE suffix when both load and target are present', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 8 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('RPE 8');
  });

  it('formats an RIR suffix', () => {
    const effortTarget: EffortTarget = { method: 'rir', value: 2 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('RIR 2');
  });

  it('formats a Borg suffix', () => {
    const effortTarget: EffortTarget = { method: 'borg', value: 18 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('Borg 18');
  });

  it('formats a percent_1rm suffix as a rounded percentage with the 1RM label', () => {
    const effortTarget: EffortTarget = { method: 'percent_1rm', pct: 0.8, target_load: 80 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('80% 1RM');
  });
});
