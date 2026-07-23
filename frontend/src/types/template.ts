export interface RequiredInput {
  key: string;
  label: string;
  type: 'number' | 'text';
  applies_to?: string;
}

export interface Slot {
  pattern?: string;
  region?: string;
  priority: string;
  scheme: string;
  muscles?: string[];
}

export interface Session {
  key: string;
  name: string;
  order: number;
  slots: Slot[];
}

export interface Scheme {
  sets: number;
  reps_min: number;
  reps_max: number;
  rest_seconds: number;
  target_rpe?: number;
  intensity_pct?: number;
}

export interface ProgressionRef {
  model_key: string;
  params: Record<string, unknown>;
  deload_every?: number;
}

export interface Template {
  slug: string;
  name: string;
  description: string;
  goals: string[];
  experience_levels: string[];
  days_per_week_min: number;
  days_per_week_max: number;
  session_duration_min: number;
  session_duration_max: number;
  split: {
    sessions: Session[];
    schemes: Record<string, Scheme>;
  };
  progression_ref: ProgressionRef;
  required_inputs: RequiredInput[];
}
