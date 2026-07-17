export type BodyRegion = 'upper_body' | 'lower_body' | 'core' | 'full_body';

export type MovementPattern =
  | 'squat'
  | 'hinge'
  | 'lunge'
  | 'horizontal_push'
  | 'vertical_push'
  | 'horizontal_pull'
  | 'vertical_pull'
  | 'rotation'
  | 'anti_rotation'
  | 'carry'
  | 'isolation'
  | 'locomotion'
  | 'mobility';

export type Equipment =
  | 'barbell'
  | 'dumbbells'
  | 'cable_machine'
  | 'machine'
  | 'kettlebell'
  | 'resistance_bands'
  | 'medicine_ball'
  | 'gymnastics_rings'
  | 'none';

export type Muscle =
  | 'abs'
  | 'biceps'
  | 'calves'
  | 'chest'
  | 'glutes'
  | 'hamstrings'
  | 'lats'
  | 'quads'
  | 'shoulders_anterior'
  | 'shoulders_lateral'
  | 'shoulders_posterior'
  | 'triceps'
  | 'traps';

export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';

export interface ExerciseResponse {
  id: number;
  name: string;
  slug: string;
  movement_slug: string;
  body_region: BodyRegion;
  movement_pattern: MovementPattern;
  primary_muscles: Muscle[];
  secondary_muscles: Muscle[];
  equipment_tags: Equipment[];
  difficulty_level: ExperienceLevel;
  instructions: string;
  form_cues: string[];
  safety_notes: string | null;
  is_unilateral: boolean;
  is_compound: boolean;
  created_at: string;
  updated_at: string;
}

// UI-friendly exercise format
export interface Exercise {
  id: number;
  name: string;
  muscleGroup: string;
  equipment: string[];
  difficulty: string;
  description: string;
  targetMuscles: string[];
  instructions: string;
  formCues: string[];
  safetyNotes: string | null;
}

export interface ExerciseGroup {
  muscleGroup: string;
  exercises: Exercise[];
}
