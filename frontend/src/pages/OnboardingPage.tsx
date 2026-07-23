import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { saveUserProfile } from '@/api/auth';
import { createTrainingEnvironment } from '@/api/trainingEnvironments';
import { createInjuryRecord } from '@/api/injuries';
import { getErrorMessage } from '@/api/errors';
import {
  Button,
  FormField,
  Card,
  Alert,
  TrainingEnvironmentCard,
  TrainingEnvironmentForm,
  InjuryRecordCard,
  InjuryRecordForm,
} from '@/components';
import type { TrainingEnvironment, TrainingEnvironmentPayload } from '@/types/trainingEnvironment';
import type { InjuryRecord, InjuryRecordPayload } from '@/types/injury';

type OnboardingFormData = {
  age: string;
  gender: string;
  weight_kg: string;
  height_cm: string;
  activity_level: string;
  fitness_focus: string;
  experience_level: string;
  days_per_week: string;
  workout_duration_min: string;
  short_term_goals: string;
  medium_term_goals: string;
};

const GOAL_LABELS: Record<string, string> = {
  strength: 'Strength',
  endurance: 'Endurance',
  weight_loss: 'Weight Loss',
  muscle_gain: 'Muscle Gain',
  flexibility: 'Flexibility',
  general: 'General Fitness',
};

const STEPS: { title: string; requiredFields: (keyof OnboardingFormData)[] }[] = [
  { title: 'Personal Information', requiredFields: ['age', 'gender', 'weight_kg', 'height_cm'] },
  { title: 'Fitness Level', requiredFields: ['experience_level', 'activity_level'] },
  {
    title: 'Workout Preferences',
    requiredFields: ['fitness_focus', 'days_per_week', 'workout_duration_min'],
  },
  { title: 'Training Environments', requiredFields: [] },
  { title: 'Your Goals', requiredFields: [] },
  { title: 'Injuries & Limitations', requiredFields: [] },
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const setUserProfile = useAuthStore((state) => state.setUserProfile);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<OnboardingFormData>({
    age: '',
    gender: '',
    weight_kg: '',
    height_cm: '',
    activity_level: '',
    fitness_focus: '',
    experience_level: '',
    days_per_week: '',
    workout_duration_min: '',
    short_term_goals: '',
    medium_term_goals: '',
  });
  const [environments, setEnvironments] = useState<TrainingEnvironment[]>([]);
  const [showAddEnvironment, setShowAddEnvironment] = useState(false);
  const [environmentError, setEnvironmentError] = useState<string | null>(null);
  const [injuries, setInjuries] = useState<InjuryRecord[]>([]);
  const [showAddInjury, setShowAddInjury] = useState(false);
  const [injuryError, setInjuryError] = useState<string | null>(null);
  const [goalWeights, setGoalWeights] = useState<Record<string, number>>({});
  const [showGoalWeights, setShowGoalWeights] = useState(false);

  const isLastStep = currentStep === STEPS.length - 1;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleNext = () => {
    const missingFields = STEPS[currentStep].requiredFields.filter((field) => !formData[field]);
    if (missingFields.length > 0) {
      setError('Please fill in all required fields before continuing.');
      return;
    }
    setError(null);
    setCurrentStep((step) => step + 1);
  };

  const handleBack = () => {
    setError(null);
    setCurrentStep((step) => step - 1);
  };

  const handleGoalWeightChange = (goal: string, value: number) => {
    setGoalWeights((prev) => ({ ...prev, [goal]: value / 100 }));
  };

  const handleAddEnvironment = async (payload: TrainingEnvironmentPayload) => {
    setEnvironmentError(null);
    try {
      const environment = await createTrainingEnvironment(payload);
      setEnvironments((prev) => [...prev, environment]);
      setShowAddEnvironment(false);
    } catch (err) {
      setEnvironmentError(getErrorMessage(err));
    }
  };

  const handleAddInjury = async (payload: InjuryRecordPayload) => {
    setInjuryError(null);
    try {
      const injury = await createInjuryRecord(payload);
      setInjuries((prev) => [...prev, injury]);
      setShowAddInjury(false);
    } catch (err) {
      setInjuryError(getErrorMessage(err));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isLastStep) {
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const profileData = {
        age: parseInt(formData.age) || undefined,
        gender: formData.gender || undefined,
        weight_kg: parseFloat(formData.weight_kg) || undefined,
        height_cm: parseInt(formData.height_cm) || undefined,
        activity_level: formData.activity_level || undefined,
        fitness_focus: formData.fitness_focus || undefined,
        experience_level: formData.experience_level || undefined,
        days_per_week: parseInt(formData.days_per_week) || undefined,
        workout_duration_min: parseInt(formData.workout_duration_min) || undefined,
        short_term_goals: formData.short_term_goals || undefined,
        medium_term_goals: formData.medium_term_goals || undefined,
        goal_weights: Object.values(goalWeights).some((v) => v > 0)
          ? Object.fromEntries(Object.entries(goalWeights).filter(([, v]) => v > 0))
          : undefined,
      };

      const response = await saveUserProfile(profileData);
      if (!response.profile) {
        throw new Error('Failed to save profile');
      }
      setUserProfile(response.profile);
      navigate('/');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <Card className="card-elevated mb-8">
          <div className="mb-8">
            <h1 className="display-md mb-2">Welcome, {user?.first_name}! 🎉</h1>
            <p className="body-lg text-neutral-600 dark:text-neutral-400">
              Let's set up your fitness profile to create your personalized workout program.
            </p>
          </div>

          {/* Progress Indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <p className="label-sm text-neutral-600 dark:text-neutral-400">
                Step {currentStep + 1} of {STEPS.length}
              </p>
              <p className="label-sm text-neutral-600 dark:text-neutral-400">
                {Math.round(((currentStep + 1) / STEPS.length) * 100)}%
              </p>
            </div>
            <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2 overflow-hidden">
              <div
                className="h-2 rounded-full bg-primary-600 dark:bg-primary-500 transition-all duration-500"
                style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
              />
            </div>
          </div>

          {error && (
            <Alert type="error" dismissible onDismiss={() => setError(null)} className="mb-6">
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Personal Info */}
            {currentStep === 0 && (
              <div>
                <h2 className="heading-md mb-6">Personal Information</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FormField
                    label="Age"
                    type="number"
                    name="age"
                    value={formData.age}
                    onChange={handleChange}
                    required
                    min="13"
                    max="120"
                  />
                  <div className="input-group">
                    <label htmlFor="gender" className="input-label">
                      Gender <span className="text-error-600">*</span>
                    </label>
                    <select
                      id="gender"
                      name="gender"
                      value={formData.gender}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select gender</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <FormField
                    label="Weight (kg)"
                    type="number"
                    name="weight_kg"
                    value={formData.weight_kg}
                    onChange={handleChange}
                    required
                    min="20"
                    max="500"
                    step="0.1"
                  />
                  <FormField
                    label="Height (cm)"
                    type="number"
                    name="height_cm"
                    value={formData.height_cm}
                    onChange={handleChange}
                    required
                    min="100"
                    max="250"
                  />
                </div>
              </div>
            )}

            {/* Fitness Level */}
            {currentStep === 1 && (
              <div>
                <h2 className="heading-md mb-6">Fitness Level</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="input-group">
                    <label htmlFor="experience" className="input-label">
                      Experience Level <span className="text-error-600">*</span>
                    </label>
                    <select
                      id="experience"
                      name="experience_level"
                      value={formData.experience_level}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select level</option>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label htmlFor="activity" className="input-label">
                      Activity Level <span className="text-error-600">*</span>
                    </label>
                    <select
                      id="activity"
                      name="activity_level"
                      value={formData.activity_level}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select level</option>
                      <option value="sedentary">Sedentary</option>
                      <option value="lightly_active">Lightly Active</option>
                      <option value="moderately_active">Moderately Active</option>
                      <option value="very_active">Very Active</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Workout Preferences */}
            {currentStep === 2 && (
              <div>
                <h2 className="heading-md mb-6">Workout Preferences</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="input-group">
                    <label htmlFor="focus" className="input-label">
                      Fitness Focus <span className="text-error-600">*</span>
                    </label>
                    <select
                      id="focus"
                      name="fitness_focus"
                      value={formData.fitness_focus}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select focus</option>
                      <option value="strength">Strength</option>
                      <option value="endurance">Endurance</option>
                      <option value="flexibility">Flexibility</option>
                      <option value="weight_loss">Weight Loss</option>
                      <option value="muscle_gain">Muscle Gain</option>
                      <option value="general">General Fitness</option>
                    </select>
                  </div>
                  <FormField
                    label="Days per Week"
                    type="number"
                    name="days_per_week"
                    value={formData.days_per_week}
                    onChange={handleChange}
                    required
                    min="1"
                    max="7"
                  />
                  <FormField
                    label="Workout Duration (minutes)"
                    type="number"
                    name="workout_duration_min"
                    value={formData.workout_duration_min}
                    onChange={handleChange}
                    required
                    min="15"
                    max="300"
                    step="15"
                  />
                </div>

                <div className="mt-4">
                  <button
                    type="button"
                    onClick={() => setShowGoalWeights((v) => !v)}
                    className="text-sm text-primary-600 dark:text-primary-400 font-medium hover:underline"
                  >
                    {showGoalWeights ? 'Hide' : 'Fine-tune your goal mix (optional)'}
                  </button>
                  {showGoalWeights && (
                    <div className="mt-3 space-y-3">
                      {Object.entries(GOAL_LABELS).map(([goal, label]) => (
                        <div key={goal} className="flex items-center gap-3">
                          <label
                            htmlFor={`goal-weight-${goal}`}
                            className="text-sm text-neutral-700 dark:text-neutral-300 w-32 flex-shrink-0"
                          >
                            {label}
                          </label>
                          <input
                            id={`goal-weight-${goal}`}
                            type="range"
                            min="0"
                            max="100"
                            step="5"
                            value={Math.round((goalWeights[goal] ?? 0) * 100)}
                            onChange={(e) => handleGoalWeightChange(goal, Number(e.target.value))}
                            className="flex-1"
                          />
                          <span className="text-sm text-neutral-500 dark:text-neutral-400 w-10 text-right flex-shrink-0">
                            {Math.round((goalWeights[goal] ?? 0) * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Training Environments */}
            {currentStep === 3 && (
              <div>
                <h2 className="heading-md mb-4">Training Environments</h2>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                  Tell us where you train (e.g., a commercial gym, your home setup, or
                  bodyweight-only). This step is optional — you can skip it and add environments
                  later.
                </p>

                {showAddEnvironment && (
                  <p className="text-sm text-primary-700 dark:text-primary-400 mb-4 font-medium">
                    Click "Save Environment" below to add it to your list — the wizard's Next button
                    won't save it for you.
                  </p>
                )}

                {environmentError && (
                  <Alert
                    type="error"
                    dismissible
                    onDismiss={() => setEnvironmentError(null)}
                    className="mb-4"
                  >
                    {environmentError}
                  </Alert>
                )}

                {environments.length > 0 && (
                  <div className="space-y-3 mb-4">
                    {environments.map((environment) => (
                      <TrainingEnvironmentCard
                        key={environment.id}
                        environment={environment}
                        readOnly
                      />
                    ))}
                  </div>
                )}

                {showAddEnvironment ? (
                  <TrainingEnvironmentForm
                    onSubmit={handleAddEnvironment}
                    onCancel={() => setShowAddEnvironment(false)}
                  />
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setShowAddEnvironment(true)}
                  >
                    Add Environment
                  </Button>
                )}
              </div>
            )}

            {/* Goals */}
            {currentStep === 4 && (
              <div>
                <h2 className="heading-md mb-6">Your Goals</h2>
                <div className="space-y-4">
                  <FormField
                    label="Short-term Goals"
                    name="short_term_goals"
                    value={formData.short_term_goals}
                    onChange={handleChange}
                    placeholder="e.g., Build a consistent workout habit"
                  />
                  <FormField
                    label="Medium-term Goals"
                    name="medium_term_goals"
                    value={formData.medium_term_goals}
                    onChange={handleChange}
                    placeholder="e.g., Gain muscle and improve endurance"
                  />
                </div>
              </div>
            )}

            {/* Injuries & Limitations */}
            {currentStep === 5 && (
              <div>
                <h2 className="heading-md mb-4">Injuries & Limitations</h2>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                  Tell us about any injuries or physical limitations so we can avoid exercises that
                  aggravate them. This step is optional — you can skip it and add these later from
                  your profile.
                </p>

                {showAddInjury && (
                  <p className="text-sm text-primary-700 dark:text-primary-400 mb-4 font-medium">
                    Click "Add Injury" below to add it to your list — the wizard's Next button won't
                    save it for you.
                  </p>
                )}

                {injuryError && (
                  <Alert
                    type="error"
                    dismissible
                    onDismiss={() => setInjuryError(null)}
                    className="mb-4"
                  >
                    {injuryError}
                  </Alert>
                )}

                {injuries.length > 0 && (
                  <div className="space-y-3 mb-4">
                    {injuries.map((injury) => (
                      <InjuryRecordCard key={injury.id} injury={injury} />
                    ))}
                  </div>
                )}

                {showAddInjury ? (
                  <InjuryRecordForm
                    onSubmit={handleAddInjury}
                    onCancel={() => setShowAddInjury(false)}
                  />
                ) : (
                  <Button type="button" variant="secondary" onClick={() => setShowAddInjury(true)}>
                    Add Injury
                  </Button>
                )}
              </div>
            )}

            <div className="flex items-center justify-between gap-4 pt-6">
              {currentStep > 0 ? (
                <Button
                  type="button"
                  className="btn btn-outline"
                  onClick={handleBack}
                  disabled={showAddEnvironment}
                >
                  Back
                </Button>
              ) : (
                <span />
              )}

              {isLastStep ? (
                <Button type="submit" className="btn btn-success" disabled={loading}>
                  {loading ? 'Completing...' : 'Complete Onboarding'}
                </Button>
              ) : (
                <Button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleNext}
                  disabled={showAddEnvironment}
                >
                  Next
                </Button>
              )}
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
