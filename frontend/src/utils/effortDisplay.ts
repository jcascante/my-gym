import type { WeightUnit } from '@/types/programCreation';
import type { EffortTarget } from '@/types/program';

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
    switch (effortTarget.method) {
      case 'percent_1rm':
        return `${baseFormat} @${effortTarget.pct}%`;
      case 'rir':
        return `${baseFormat} @RIR ${effortTarget.value}`;
      case 'rpe':
        return `${baseFormat} @RPE ${effortTarget.value}`;
      case 'borg':
        return `${baseFormat} @Borg ${effortTarget.value}`;
    }
  }

  // Fallback to just sets x reps
  return baseFormat;
}
