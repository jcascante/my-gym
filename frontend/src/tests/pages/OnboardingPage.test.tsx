import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OnboardingPage from '@/pages/OnboardingPage';
import * as authApi from '@/api/auth';
import * as trainingEnvironmentsApi from '@/api/trainingEnvironments';
import { useAuthStore } from '@/store/auth';

vi.mock('@/api/auth');
vi.mock('@/api/trainingEnvironments');
vi.mock('@/store/auth');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderOnboardingPage(setUserProfileMock = vi.fn()) {
  vi.mocked(useAuthStore).mockImplementation((selector: any) =>
    selector({
      user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
      setUserProfile: setUserProfileMock,
    }),
  );

  render(
    <BrowserRouter>
      <OnboardingPage />
    </BrowserRouter>,
  );
}

async function fillPersonalInfoStep({
  age = '30',
  gender = 'male',
  weight_kg = '75.5',
  height_cm = '180',
}: Partial<Record<'age' | 'gender' | 'weight_kg' | 'height_cm', string>> = {}) {
  fireEvent.change(screen.getByLabelText(/Age/), { target: { value: age } });
  fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: gender } });
  fireEvent.change(screen.getByLabelText(/Weight \(kg\)/), { target: { value: weight_kg } });
  fireEvent.change(screen.getByLabelText(/Height \(cm\)/), { target: { value: height_cm } });
  fireEvent.click(screen.getByRole('button', { name: /Next/i }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /Fitness Level/ })).toBeInTheDocument(),
  );
}

async function fillFitnessLevelStep({
  experience_level = 'intermediate',
  activity_level = 'moderately_active',
}: Partial<Record<'experience_level' | 'activity_level', string>> = {}) {
  fireEvent.change(screen.getByLabelText(/Experience Level/), {
    target: { value: experience_level },
  });
  fireEvent.change(screen.getByLabelText(/Activity Level/), {
    target: { value: activity_level },
  });
  fireEvent.click(screen.getByRole('button', { name: /Next/i }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /Workout Preferences/ })).toBeInTheDocument(),
  );
}

async function fillWorkoutPreferencesStep({
  fitness_focus = 'strength',
  days_per_week = '4',
  workout_duration_min = '60',
}: Partial<Record<'fitness_focus' | 'days_per_week' | 'workout_duration_min', string>> = {}) {
  fireEvent.change(screen.getByLabelText(/Fitness Focus/), { target: { value: fitness_focus } });
  fireEvent.change(screen.getByLabelText(/Days per Week/), { target: { value: days_per_week } });
  fireEvent.change(screen.getByLabelText(/Workout Duration/), {
    target: { value: workout_duration_min },
  });
  fireEvent.click(screen.getByRole('button', { name: /Next/i }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /Training Environments/ })).toBeInTheDocument(),
  );
}

async function skipTrainingEnvironmentsStep() {
  fireEvent.click(screen.getByRole('button', { name: /Next/i }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /Your Goals/ })).toBeInTheDocument(),
  );
}

async function advanceThroughGoalsAndAdditionalInfoSteps() {
  fireEvent.click(screen.getByRole('button', { name: /Next/i }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /Additional Information/ })).toBeInTheDocument(),
  );
}

async function completeOnboardingSkippingEnvironments() {
  await fillPersonalInfoStep();
  await fillFitnessLevelStep();
  await fillWorkoutPreferencesStep();
  await skipTrainingEnvironmentsStep();
  await advanceThroughGoalsAndAdditionalInfoSteps();
}

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('should render the first wizard step', () => {
    renderOnboardingPage();

    expect(screen.getByText(/Welcome, John!/)).toBeInTheDocument();
    expect(screen.getByText(/Let's set up your fitness profile/)).toBeInTheDocument();
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Personal Information/ })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Fitness Level/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
  });

  it('should not advance to the next step when required fields are missing', async () => {
    renderOnboardingPage();

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(
        screen.getByText('Please fill in all required fields before continuing.'),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/Step 1 of 6/)).toBeInTheDocument();
  });

  it('should navigate back to a previous step', async () => {
    renderOnboardingPage();

    await fillPersonalInfoStep();
    expect(screen.getByText('Step 2 of 6')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Back/i }));

    await waitFor(() => expect(screen.getByText('Step 1 of 6')).toBeInTheDocument());
    expect(screen.getByLabelText(/Age/)).toHaveValue(30);
  });

  it('should allow completing onboarding without adding a training environment', async () => {
    const setUserProfileMock = vi.fn();
    const mockResponse = {
      id: 1,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        id: 1,
        age: 30,
        gender: 'male',
        weight_kg: 75.5,
        height_cm: 180,
        activity_level: 'moderately_active',
        fitness_focus: 'strength',
        experience_level: 'intermediate',
        days_per_week: 4,
        workout_duration_min: 60,
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderOnboardingPage(setUserProfileMock);

    await completeOnboardingSkippingEnvironments();

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          age: 30,
          gender: 'male',
          weight_kg: 75.5,
          fitness_focus: 'strength',
        }),
      );
      expect(trainingEnvironmentsApi.createTrainingEnvironment).not.toHaveBeenCalled();
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should allow adding a training environment before continuing', async () => {
    const setUserProfileMock = vi.fn();
    const mockEnvironment = {
      id: 1,
      name: 'Home Gym',
      environment_type: 'home' as const,
      equipment_tags: [],
      is_default: false,
    };
    vi.mocked(trainingEnvironmentsApi.createTrainingEnvironment).mockResolvedValue(mockEnvironment);

    const mockResponse = {
      id: 1,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: { id: 1, age: 30, gender: 'male' },
    };
    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderOnboardingPage(setUserProfileMock);

    await fillPersonalInfoStep();
    await fillFitnessLevelStep();
    await fillWorkoutPreferencesStep();

    fireEvent.click(screen.getByRole('button', { name: /Add Environment/i }));
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'Home Gym' } });
    fireEvent.click(screen.getByRole('button', { name: /Save Environment/i }));

    await waitFor(() => {
      expect(trainingEnvironmentsApi.createTrainingEnvironment).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Home Gym' }),
      );
      expect(screen.getByText('Home Gym')).toBeInTheDocument();
    });

    await skipTrainingEnvironmentsStep();
    await advanceThroughGoalsAndAdditionalInfoSteps();

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should submit profile with minimal required fields', async () => {
    const setUserProfileMock = vi.fn();
    const mockResponse = {
      id: 1,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        id: 1,
        age: 25,
        gender: 'male',
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderOnboardingPage(setUserProfileMock);

    await fillPersonalInfoStep({ age: '25' });
    await fillFitnessLevelStep({ experience_level: 'beginner', activity_level: 'sedentary' });
    await fillWorkoutPreferencesStep({
      days_per_week: '1',
      workout_duration_min: '15',
    });
    await skipTrainingEnvironmentsStep();
    await advanceThroughGoalsAndAdditionalInfoSteps();

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalled();
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should display error on profile save failure', async () => {
    const setUserProfileMock = vi.fn();
    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    renderOnboardingPage(setUserProfileMock);

    await completeOnboardingSkippingEnvironments();

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('should dismiss error message', async () => {
    const setUserProfileMock = vi.fn();
    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    renderOnboardingPage(setUserProfileMock);

    await completeOnboardingSkippingEnvironments();

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
});
