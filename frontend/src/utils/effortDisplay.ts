import type { WeightUnit } from '@/types/programCreation';
import type { EffortTarget } from '@/types/program';

function effortLabel(effortTarget: EffortTarget): string {
  switch (effortTarget.method) {
    case 'percent_1rm':
      return `${Math.round((effortTarget.pct ?? 0) * 100)}% 1RM`;
    case 'rir':
      return `RIR ${effortTarget.value}`;
    case 'rpe':
      return `RPE ${effortTarget.value}`;
    case 'borg':
      return `Borg ${effortTarget.value}`;
  }
}

export function formatEffortDisplay(
  sets: number,
  reps: number,
  load: number | null,
  weightUnit: WeightUnit,
  effortTarget: EffortTarget | null,
): string {
  const baseFormat = `${sets} x ${reps}`;

  // Weight-based effort is preferred
  if (load !== null) {
    return `${baseFormat} @${load} ${weightUnit}`;
  }

  // Fall back to effort target if no weight
  if (effortTarget) {
    return `${baseFormat} @${effortLabel(effortTarget)}`;
  }

  // Fallback to just sets x reps
  return baseFormat;
}

// The counterpart to formatEffortDisplay's precedence rule: when a load is present,
// formatEffortDisplay's output already carries the weight and drops the effort target
// entirely. This renders that dropped target as a standalone qualifier instead of
// folding it back into the same string, so a loaded slot can show both.
export function formatEffortSuffix(
  load: number | null,
  effortTarget: EffortTarget | null,
): string | null {
  if (load === null || !effortTarget) {
    return null;
  }
  return effortLabel(effortTarget);
}
