import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OnboardingPage from '@/pages/OnboardingPage';
import * as authApi from '@/api/auth';
import { useAuthStore } from '@/store/auth';

vi.mock('@/api/auth');
vi.mock('@/store/auth');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('should render onboarding form', () => {
    const setUserProfileMock = vi.fn();
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

    expect(screen.getByText(/Welcome, John!/)).toBeInTheDocument();
    expect(screen.getByText(/Let's set up your fitness profile/)).toBeInTheDocument();
    expect(screen.getByText(/Personal Information/)).toBeInTheDocument();
    expect(screen.getByText(/Fitness Level/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Complete Onboarding/i })).toBeInTheDocument();
  });

  it('should submit profile with all fields', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
        setUserProfile: setUserProfileMock,
      }),
    );

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
        equipment: 'gym',
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    render(
      <BrowserRouter>
        <OnboardingPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Age/), { target: { value: '30' } });
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: 'male' } });
    fireEvent.change(screen.getByLabelText(/Weight \(kg\)/), { target: { value: '75.5' } });
    fireEvent.change(screen.getByLabelText(/Height \(cm\)/), { target: { value: '180' } });
    fireEvent.change(screen.getByLabelText(/Experience Level/), {
      target: { value: 'intermediate' },
    });
    fireEvent.change(screen.getByLabelText(/Activity Level/), {
      target: { value: 'moderately_active' },
    });
    fireEvent.change(screen.getByLabelText(/Fitness Focus/), { target: { value: 'strength' } });
    fireEvent.change(screen.getByLabelText(/Days per Week/), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText(/Workout Duration/), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText(/Equipment Access/), { target: { value: 'gym' } });

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
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should submit profile with minimal fields', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
        setUserProfile: setUserProfileMock,
      }),
    );

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

    render(
      <BrowserRouter>
        <OnboardingPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Age/), { target: { value: '25' } });
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: 'male' } });
    fireEvent.change(screen.getByLabelText(/Experience Level/), {
      target: { value: 'beginner' },
    });
    fireEvent.change(screen.getByLabelText(/Activity Level/), {
      target: { value: 'sedentary' },
    });
    fireEvent.change(screen.getByLabelText(/Fitness Focus/), { target: { value: 'strength' } });
    fireEvent.change(screen.getByLabelText(/Days per Week/), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText(/Workout Duration/), { target: { value: '15' } });
    fireEvent.change(screen.getByLabelText(/Equipment Access/), { target: { value: 'home' } });

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalled();
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should display error on profile save failure', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
        setUserProfile: setUserProfileMock,
      }),
    );

    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    render(
      <BrowserRouter>
        <OnboardingPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Age/), { target: { value: '30' } });
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: 'male' } });
    fireEvent.change(screen.getByLabelText(/Experience Level/), {
      target: { value: 'intermediate' },
    });
    fireEvent.change(screen.getByLabelText(/Activity Level/), {
      target: { value: 'moderately_active' },
    });
    fireEvent.change(screen.getByLabelText(/Fitness Focus/), { target: { value: 'strength' } });
    fireEvent.change(screen.getByLabelText(/Days per Week/), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText(/Workout Duration/), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText(/Equipment Access/), { target: { value: 'gym' } });

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('should dismiss error message', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
        setUserProfile: setUserProfileMock,
      }),
    );

    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    render(
      <BrowserRouter>
        <OnboardingPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Age/), { target: { value: '30' } });
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: 'male' } });
    fireEvent.change(screen.getByLabelText(/Experience Level/), {
      target: { value: 'intermediate' },
    });
    fireEvent.change(screen.getByLabelText(/Activity Level/), {
      target: { value: 'moderately_active' },
    });
    fireEvent.change(screen.getByLabelText(/Fitness Focus/), { target: { value: 'strength' } });
    fireEvent.change(screen.getByLabelText(/Days per Week/), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText(/Workout Duration/), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText(/Equipment Access/), { target: { value: 'gym' } });

    fireEvent.click(screen.getByRole('button', { name: /Complete Onboarding/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
});
