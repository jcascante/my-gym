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

export type EffortMethod = 'rpe' | 'rir' | 'borg' | 'percent_1rm';

export const EFFORT_METHOD_OPTIONS: { value: EffortMethod | ''; label: string }[] = [
  { value: '', label: 'Not sure yet / skip' },
  { value: 'rpe', label: 'RPE — Rate of Perceived Exertion (1-10)' },
  { value: 'rir', label: 'RIR — Reps in Reserve' },
  { value: 'borg', label: 'Borg Scale (6-20)' },
  { value: 'percent_1rm', label: '% of 1-Rep Max' },
];

export type EquipmentFamily =
  'dumbbells' | 'barbells' | 'machines' | 'bodyweight' | 'cables' | 'kettlebells';

export const EQUIPMENT_FAMILY_OPTIONS: { value: EquipmentFamily; label: string }[] = [
  { value: 'dumbbells', label: 'Dumbbells' },
  { value: 'barbells', label: 'Barbells' },
  { value: 'machines', label: 'Machines' },
  { value: 'bodyweight', label: 'Bodyweight' },
  { value: 'cables', label: 'Cables' },
  { value: 'kettlebells', label: 'Kettlebells' },
];

export type VarietyPreference = 'low' | 'medium' | 'high';

export const VARIETY_PREFERENCE_OPTIONS: { value: VarietyPreference; label: string }[] = [
  { value: 'low', label: 'Low — Stick with core exercises' },
  { value: 'medium', label: 'Medium — Balanced variety' },
  { value: 'high', label: 'High — Maximum variety' },
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
  effort_method: EffortMethod | '';
  movement_preferences?: Record<EquipmentFamily, number>;
  complementary_focus?: boolean;
  variety_preference?: VarietyPreference;
}
