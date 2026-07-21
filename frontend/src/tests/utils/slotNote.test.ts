import { it, expect } from 'vitest';
import { formatSlotNote } from '@/utils/slotNote';

it('labels a deload note', () => {
  expect(formatSlotNote('deload')).toBe('Deload week');
});

it('labels a ramp_capped note', () => {
  expect(formatSlotNote('ramp_capped')).toBe('Capped for safe progression');
});

it('renders an unrecognized note as-is', () => {
  expect(formatSlotNote('Go heavy')).toBe('Go heavy');
});
