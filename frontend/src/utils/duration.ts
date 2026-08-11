export function formatDurationWeeks(min: number, max: number): string {
  return min === max ? `${min} weeks` : `${min}-${max} weeks`;
}
