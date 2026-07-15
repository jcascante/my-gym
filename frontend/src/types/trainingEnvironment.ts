export type EnvironmentType =
  | 'commercial_gym'
  | 'home'
  | 'bodyweight'
  | 'crossfit_box'
  | 'powerlifting_gym'
  | 'strength_gym'
  | 'other';

export const ENVIRONMENT_TYPE_OPTIONS: { value: EnvironmentType; label: string }[] = [
  { value: 'commercial_gym', label: 'Commercial Gym' },
  { value: 'home', label: 'Home' },
  { value: 'bodyweight', label: 'Bodyweight Only' },
  { value: 'crossfit_box', label: 'CrossFit Box' },
  { value: 'powerlifting_gym', label: 'Powerlifting Gym' },
  { value: 'strength_gym', label: 'Strength Gym' },
  { value: 'other', label: 'Other' },
];

// Kept in sync with backend/app/core/constants.py:EQUIPMENT_CATEGORIES
export const EQUIPMENT_CATEGORIES: {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}[] = [
  {
    key: 'free_weights',
    label: 'Free Weights',
    options: [
      { value: 'barbell', label: 'Barbell' },
      { value: 'ez_bar', label: 'EZ Bar' },
      { value: 'dumbbells', label: 'Dumbbells' },
      { value: 'kettlebell', label: 'Kettlebell' },
      { value: 'medicine_ball', label: 'Medicine Ball' },
    ],
  },
  {
    key: 'machines',
    label: 'Machines',
    options: [
      { value: 'cable_machine', label: 'Cable Machine' },
      { value: 'smith_machine', label: 'Smith Machine' },
      { value: 'leg_press_machine', label: 'Leg Press' },
      { value: 'hack_squat_machine', label: 'Hack Squat Machine' },
      { value: 'chest_press_machine', label: 'Chest Press Machine' },
      { value: 'shoulder_press_machine', label: 'Shoulder Press Machine' },
      { value: 'seated_row_machine', label: 'Seated Row Machine' },
      { value: 'assisted_dip_machine', label: 'Assisted Dip Machine' },
      { value: 'assisted_pullup_machine', label: 'Assisted Pull-up Machine' },
      { value: 'calf_raise_machine', label: 'Calf Raise Machine' },
      { value: 'leg_extension_machine', label: 'Leg Extension Machine' },
      { value: 'leg_curl_machine', label: 'Leg Curl Machine' },
      { value: 'hip_abduction_machine', label: 'Hip Abduction Machine' },
      { value: 'hip_adduction_machine', label: 'Hip Adduction Machine' },
      { value: 'lat_pulldown_machine', label: 'Lat Pulldown Machine' },
      { value: 'pec_deck_machine', label: 'Pec Deck Machine' },
    ],
  },
  {
    key: 'racks_and_benches',
    label: 'Racks & Benches',
    options: [
      { value: 'squat_rack', label: 'Squat Rack' },
      { value: 'bench', label: 'Bench' },
    ],
  },
  {
    key: 'cardio',
    label: 'Cardio',
    options: [
      { value: 'treadmill', label: 'Treadmill' },
      { value: 'stationary_bike', label: 'Stationary Bike' },
      { value: 'rowing_machine', label: 'Rowing Machine' },
      { value: 'stair_climber', label: 'Stair Climber' },
      { value: 'assault_bike', label: 'Assault Bike' },
    ],
  },
  {
    key: 'bodyweight_and_accessories',
    label: 'Bodyweight & Accessories',
    options: [
      { value: 'pull_up_bar', label: 'Pull-up Bar' },
      { value: 'resistance_bands', label: 'Resistance Bands' },
      { value: 'ab_wheel', label: 'Ab Wheel' },
      { value: 'gymnastic_rings', label: 'Gymnastic Rings' },
      { value: 'plyo_box', label: 'Plyo Box' },
      { value: 'jump_rope', label: 'Jump Rope' },
      { value: 'battle_ropes', label: 'Battle Ropes' },
      { value: 'sandbag', label: 'Sandbag' },
      { value: 'sled', label: 'Sled' },
      { value: 'none', label: 'None' },
    ],
  },
];

// Flattened for lookups (e.g. rendering a tag's label from its value).
export const EQUIPMENT_OPTIONS = EQUIPMENT_CATEGORIES.flatMap((category) => category.options);

// Kept in sync with backend/app/core/constants.py:ENVIRONMENT_TYPE_EQUIPMENT_PRESETS.
// "other" is intentionally empty - the picker treats an empty preset as "show everything."
export const ENVIRONMENT_EQUIPMENT_PRESETS: Record<EnvironmentType, string[]> = {
  commercial_gym: [
    'barbell',
    'ez_bar',
    'dumbbells',
    'kettlebell',
    'medicine_ball',
    'cable_machine',
    'smith_machine',
    'leg_press_machine',
    'hack_squat_machine',
    'chest_press_machine',
    'shoulder_press_machine',
    'seated_row_machine',
    'assisted_dip_machine',
    'assisted_pullup_machine',
    'calf_raise_machine',
    'leg_extension_machine',
    'leg_curl_machine',
    'hip_abduction_machine',
    'hip_adduction_machine',
    'lat_pulldown_machine',
    'pec_deck_machine',
    'squat_rack',
    'bench',
    'treadmill',
    'stationary_bike',
    'rowing_machine',
    'stair_climber',
    'assault_bike',
    'pull_up_bar',
    'resistance_bands',
  ],
  home: ['dumbbells', 'kettlebell', 'resistance_bands', 'bench', 'pull_up_bar', 'none'],
  bodyweight: ['none', 'pull_up_bar', 'resistance_bands'],
  crossfit_box: [
    'barbell',
    'squat_rack',
    'kettlebell',
    'medicine_ball',
    'pull_up_bar',
    'gymnastic_rings',
    'plyo_box',
    'jump_rope',
    'battle_ropes',
    'sandbag',
    'sled',
    'rowing_machine',
    'assault_bike',
  ],
  powerlifting_gym: ['barbell', 'squat_rack', 'bench', 'ez_bar', 'sled'],
  strength_gym: [
    'barbell',
    'squat_rack',
    'bench',
    'dumbbells',
    'kettlebell',
    'pull_up_bar',
    'resistance_bands',
  ],
  other: [],
};

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
