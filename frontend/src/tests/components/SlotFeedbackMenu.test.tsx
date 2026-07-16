import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SlotFeedbackMenu } from '@/components/SlotFeedbackMenu';

const slot = {
  workout_exercise_id: 9,
  exercise_id: 3,
  sets: 3,
  reps: 5,
  load: 60,
  rest_seconds: 120,
  note: null,
  is_locked: false,
  is_user_swapped: false,
};

it('emits lock action', async () => {
  const onAction = vi.fn();
  render(<SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={() => {}} />);
  await userEvent.click(screen.getByRole('button', { name: /options/i }));
  await userEvent.click(screen.getByRole('menuitem', { name: /lock/i }));
  expect(onAction).toHaveBeenCalledWith({ type: 'lock', workout_exercise_id: 9 });
});
