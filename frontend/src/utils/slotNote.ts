// Known engine-generated `note` values (deload.py / ramp_guard.py) get a friendlier
// label; anything else (e.g. a future note key, or a user-swap note) renders as-is.
const NOTE_LABELS: Record<string, string> = {
  deload: 'Deload week',
  ramp_capped: 'Capped for safe progression',
};

export function formatSlotNote(note: string): string {
  return NOTE_LABELS[note] ?? note;
}
