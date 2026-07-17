export type FocusArea = 'push' | 'pull' | 'legs' | 'core' | 'cardio' | 'flexibility' | 'full_body';

export const FOCUS_AREA_OPTIONS: { value: FocusArea; label: string }[] = [
  { value: 'push', label: 'Push (chest, shoulders, triceps)' },
  { value: 'pull', label: 'Pull (back, biceps)' },
  { value: 'legs', label: 'Legs' },
  { value: 'core', label: 'Core' },
  { value: 'cardio', label: 'Cardio' },
  { value: 'flexibility', label: 'Flexibility' },
  { value: 'full_body', label: 'Full Body' },
];

export type WeightUnit = 'kg' | 'lbs';

export const WEIGHT_UNIT_OPTIONS: { value: WeightUnit; label: string }[] = [
  { value: 'kg', label: 'Kilograms (kg)' },
  { value: 'lbs', label: 'Pounds (lbs)' },
];

export type ProgressionStyle = 'consistent' | 'variable';

export const PROGRESSION_STYLE_OPTIONS: { value: ProgressionStyle; label: string }[] = [
  { value: 'consistent', label: 'Consistent — same each week' },
  { value: 'variable', label: 'Variable — varies week to week' },
];

export type DayOfWeek =
  'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

export const DAY_OF_WEEK_OPTIONS: { value: DayOfWeek; label: string }[] = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
];

export interface ProgramCreationPayload {
  environment_id: number;
  days_per_week: number;
  preferred_days: DayOfWeek[];
  session_duration_min: number;
  start_date: string;
  focus_areas: FocusArea[];
  weight_unit: WeightUnit;
  available_weight_increments: number[];
  progression_style: ProgressionStyle;
}

export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
}
