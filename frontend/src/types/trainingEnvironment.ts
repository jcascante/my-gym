export type EnvironmentType = 'commercial_gym' | 'home' | 'bodyweight' | 'crossfit_box' | 'other';

export const ENVIRONMENT_TYPE_OPTIONS: { value: EnvironmentType; label: string }[] = [
  { value: 'commercial_gym', label: 'Commercial Gym' },
  { value: 'home', label: 'Home' },
  { value: 'bodyweight', label: 'Bodyweight Only' },
  { value: 'crossfit_box', label: 'CrossFit Box' },
  { value: 'other', label: 'Other' },
];

// Kept in sync with backend/app/core/constants.py:ALLOWED_EQUIPMENT_TAGS
export const EQUIPMENT_TAG_OPTIONS: { value: string; label: string }[] = [
  { value: 'barbell', label: 'Barbell' },
  { value: 'squat_rack', label: 'Squat Rack' },
  { value: 'dumbbells', label: 'Dumbbells' },
  { value: 'kettlebell', label: 'Kettlebell' },
  { value: 'resistance_bands', label: 'Resistance Bands' },
  { value: 'pull_up_bar', label: 'Pull-up Bar' },
  { value: 'bench', label: 'Bench' },
  { value: 'cardio_machine', label: 'Cardio Machine' },
  { value: 'cable_machine', label: 'Cable Machine' },
  { value: 'none', label: 'None' },
];

export interface TrainingEnvironment {
  id: number;
  name: string;
  environment_type: EnvironmentType;
  equipment_tags: string[];
  is_default: boolean;
}

export interface TrainingEnvironmentPayload {
  name: string;
  environment_type: EnvironmentType;
  equipment_tags: string[];
  is_default: boolean;
}
