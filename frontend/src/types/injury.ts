// Kept in sync with backend/app/models/injury.py and backend/app/models/exercise.py:Provocation

export type InjuryRegion =
  | 'shoulder'
  | 'elbow'
  | 'wrist'
  | 'cervical'
  | 'thoracic'
  | 'lumbar'
  | 'hip'
  | 'knee'
  | 'ankle_foot';

export const INJURY_REGION_OPTIONS: { value: InjuryRegion; label: string }[] = [
  { value: 'shoulder', label: 'Shoulder' },
  { value: 'elbow', label: 'Elbow' },
  { value: 'wrist', label: 'Wrist' },
  { value: 'cervical', label: 'Neck (Cervical)' },
  { value: 'thoracic', label: 'Upper Back (Thoracic)' },
  { value: 'lumbar', label: 'Lower Back (Lumbar)' },
  { value: 'hip', label: 'Hip' },
  { value: 'knee', label: 'Knee' },
  { value: 'ankle_foot', label: 'Ankle / Foot' },
];

export type InjuryCondition =
  | 'acute_pain'
  | 'post_surgical'
  | 'tendinopathy'
  | 'joint_instability'
  | 'chronic_recurrent'
  | 'resolved_cautious'
  | 'unspecified';

export const INJURY_CONDITION_OPTIONS: { value: InjuryCondition; label: string }[] = [
  { value: 'acute_pain', label: 'Acute Pain' },
  { value: 'post_surgical', label: 'Post-Surgical' },
  { value: 'tendinopathy', label: 'Tendinopathy' },
  { value: 'joint_instability', label: 'Joint Instability' },
  { value: 'chronic_recurrent', label: 'Chronic / Recurrent' },
  { value: 'resolved_cautious', label: 'Resolved (Still Cautious)' },
  { value: 'unspecified', label: 'Unspecified' },
];

export type InjuryPhase = 'acute' | 'rehabilitating' | 'resolved_cautious' | 'cleared';

export const INJURY_PHASE_OPTIONS: { value: InjuryPhase; label: string }[] = [
  { value: 'acute', label: 'Acute (just happened)' },
  { value: 'rehabilitating', label: 'Rehabilitating' },
  { value: 'resolved_cautious', label: 'Resolved (Still Cautious)' },
  { value: 'cleared', label: 'Fully Cleared' },
];

export type InjurySource = 'user_reported' | 'professional_cleared';

export const INJURY_SOURCE_OPTIONS: { value: InjurySource; label: string }[] = [
  { value: 'user_reported', label: 'Self-Reported' },
  { value: 'professional_cleared', label: 'Cleared by a Doctor/PT' },
];

export type Provocation =
  | 'overhead'
  | 'loaded_spinal_flexion'
  | 'loaded_spinal_extension'
  | 'axial_loading'
  | 'deep_knee_flexion'
  | 'deep_hip_flexion'
  | 'heavy_grip'
  | 'high_impact'
  | 'ballistic_loading'
  | 'end_range_shoulder_rotation'
  | 'wrist_extension_load'
  | 'unilateral_loading';

export const PROVOCATION_OPTIONS: { value: Provocation; label: string }[] = [
  { value: 'overhead', label: 'Overhead movements' },
  { value: 'loaded_spinal_flexion', label: 'Loaded spinal flexion (rounding under load)' },
  { value: 'loaded_spinal_extension', label: 'Loaded spinal extension (arching under load)' },
  { value: 'axial_loading', label: 'Axial loading (compression through the spine)' },
  { value: 'deep_knee_flexion', label: 'Deep knee bend' },
  { value: 'deep_hip_flexion', label: 'Deep hip flexion' },
  { value: 'heavy_grip', label: 'Heavy grip demand' },
  { value: 'high_impact', label: 'High impact / jumping' },
  { value: 'ballistic_loading', label: 'Explosive / ballistic movement' },
  { value: 'end_range_shoulder_rotation', label: 'End-range shoulder rotation' },
  { value: 'wrist_extension_load', label: 'Loaded wrist extension' },
  { value: 'unilateral_loading', label: 'Single-limb (unilateral) loading' },
];

export const SEVERITY_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: 'Mild - minor discomfort, does not limit training' },
  { value: 2, label: 'Moderate - limits some exercises' },
  { value: 3, label: 'Severe - significantly limits training' },
];

export interface InjuryRecord {
  id: number;
  region: InjuryRegion;
  condition: InjuryCondition;
  phase: InjuryPhase;
  provocations: Provocation[];
  severity: number;
  reported_at: string;
  source: InjurySource;
}

export interface InjuryRecordPayload {
  region: InjuryRegion;
  condition: InjuryCondition;
  phase: InjuryPhase;
  provocations: Provocation[];
  severity: number;
  reported_at: string;
  source: InjurySource;
}
