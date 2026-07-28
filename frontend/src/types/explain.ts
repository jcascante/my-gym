import type { Advisory } from '@/types/program';

export interface TemplateExplanation {
  template_id: number;
  slug: string;
  name: string;
  fit_pct: number;
  factors: Record<string, number>;
  tier: 'best' | 'strong' | 'possible';
  advisories: Advisory[];
}

export interface LedgerContribution {
  group: string;
  effective_sets: number;
}

export interface SlotExplanation {
  workout_exercise_id: number;
  exercise_id: number;
  exercise_name: string;
  factors: Record<string, number>;
  score: number;
  ledger_contributions: LedgerContribution[];
  safety_note: string | null;
}
