import type { ProgressionStyle, EffortMethod } from '@/types/programCreation';

export interface Advisory {
  code: string;
  severity: 'info' | 'warning' | 'error';
  message: string;
  subject: string | null;
}

export interface RequiredInput {
  key: string;
  label: string;
  type: 'number' | 'text';
  applies_to: string | null;
}

export interface TemplateMatch {
  template_id: number;
  slug: string;
  name: string;
  fit_pct: number;
  factors: Record<string, number>;
  required_inputs: RequiredInput[];
  tier: 'best' | 'strong' | 'possible';
  all_infeasible: boolean;
  advisories: Advisory[];
}

export interface EffortTarget {
  method: 'rpe' | 'rir' | 'borg' | 'percent_1rm';
  value?: number;
  pct?: number;
  target_load?: number | null;
}

export interface SlotPreview {
  workout_exercise_id: number;
  exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  is_locked: boolean;
  is_user_swapped: boolean;
  effort_target: EffortTarget | null;
  rotation_pool: number[];
}

export interface WorkoutPreview {
  workout_id: number;
  key: string;
  name: string;
  slots: SlotPreview[];
}

export interface ProgramPreview {
  program_id: number;
  name: string;
  status: 'draft' | 'active' | 'archived';
  duration_weeks: number;
  weeks: Record<string, WorkoutPreview[]>;
  advisories: Advisory[];
}

export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  fitness_focus: string;
  weight_unit: string;
  duration_weeks: number;
}

export interface DraftRequest extends MatchRequest {
  template_id: number;
  required_inputs: Record<string, number | string>;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | null;
}

export type FeedbackAction =
  | { type: 'lock' | 'exclude' | 'regenerate'; workout_exercise_id: number }
  | { type: 'swap'; workout_exercise_id: number; exercise_id: number }
  | { type: 'adjust_volume'; workout_key: string; delta: number };

export interface Alternative {
  id: number;
  name: string;
  slug: string;
}
