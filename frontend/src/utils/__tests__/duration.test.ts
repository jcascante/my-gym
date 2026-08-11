import { it, expect, describe } from 'vitest';
import { formatDurationWeeks } from '@/utils/duration';

describe('formatDurationWeeks', () => {
  it('collapses to a single value when min equals max', () => {
    expect(formatDurationWeeks(8, 8)).toBe('8 weeks');
  });

  it('shows a range when min and max differ', () => {
    expect(formatDurationWeeks(4, 12)).toBe('4-12 weeks');
  });
});
