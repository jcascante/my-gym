import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';

export type SessionStatus = 'scheduled' | 'in_progress' | 'completed' | 'missed' | 'skipped';

export interface ScheduleEntry {
  session_id: number;
  scheduled_date: string;
  week: number;
  status: SessionStatus;
  workout_id: number;
  workout_name: string;
  exercise_count: number;
  duration_min: number;
}

export interface LoggedSet {
  id: number;
  workout_exercise_id: number;
  set_number: number;
  actual_weight: number | null;
  actual_reps: number | null;
  actual_rpe: number | null;
  effort_method: string;
}

export interface SessionDetail extends ScheduleEntry {
  program_id: number;
  program_name: string;
  weight_unit: 'kg' | 'lbs';
  slots: SlotPreview[];
  logged_sets: LoggedSet[];
  completed_at: string | null;
  reactive_deload: boolean;
  deload_reason: string | null;
}

export interface SessionSetLogPayload {
  workout_exercise_id: number;
  set_number: number;
  actual_weight?: number;
  actual_reps?: number;
  actual_rpe?: number;
  effort_method?: EffortMethod;
}
