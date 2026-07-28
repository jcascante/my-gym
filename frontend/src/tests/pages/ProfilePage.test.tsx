import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProfilePage from '@/pages/ProfilePage';
import * as authApi from '@/api/auth';
import * as injuriesApi from '@/api/injuries';
import { useAuthStore } from '@/store/auth';

vi.mock('@/api/auth');
vi.mock('@/api/injuries');
vi.mock('@/store/auth');

function renderProfilePage() {
  render(
    <BrowserRouter>
      <QueryClientProvider client={new QueryClient()}>
        <ProfilePage />
      </QueryClientProvider>
    </BrowserRouter>,
  );
}

describe('ProfilePage', () => {
  const mockUser = {
    id: 1,
    email: 'john@example.com',
    first_name: 'John',
    last_name: 'Doe',
  };

  const mockUserProfile = {
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
    short_term_goals: 'Build muscle',
    medium_term_goals: 'Improve overall fitness',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(injuriesApi.listInjuryRecords).mockResolvedValue([]);
  });

  it('should render all profile fields in read-only mode', () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    renderProfilePage();

    expect(screen.getByText('My Profile')).toBeInTheDocument();
    expect(screen.getAllByText('Personal Information')).toHaveLength(2);
    expect(screen.getByText('John')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();

    expect(screen.getByText('Fitness Profile')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('male')).toBeInTheDocument();
    expect(screen.getByText('75.5 kg')).toBeInTheDocument();
    expect(screen.getByText('180 cm')).toBeInTheDocument();
    expect(screen.getByText('intermediate')).toBeInTheDocument();
    expect(screen.getByText('moderately_active')).toBeInTheDocument();
    expect(screen.getByText('strength')).toBeInTheDocument();
    expect(screen.getByText('4 days/week')).toBeInTheDocument();
    expect(screen.getByText('60 minutes')).toBeInTheDocument();
    expect(screen.getByText('Build muscle')).toBeInTheDocument();
    expect(screen.getByText('Improve overall fitness')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /Edit Profile/i })).toBeInTheDocument();
  });

  it('should render only present fields in read-only mode', () => {
    const partialProfile = {
      id: 1,
      age: 25,
      gender: 'female',
    };

    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: partialProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    renderProfilePage();

    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('female')).toBeInTheDocument();

    expect(screen.queryByText('Injuries or Limitations')).not.toBeInTheDocument();
    expect(screen.queryByText('Goals')).not.toBeInTheDocument();
  });

  it('should enter edit mode with pre-filled fields when Edit button clicked', () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();

    const ageInput = screen.getByLabelText('Age');
    expect(ageInput).toHaveAttribute('type', 'number');
    expect(ageInput).toHaveValue(30);

    const genderSelect = screen.getByLabelText('Gender');
    expect(genderSelect).toHaveValue('male');

    const weightInput = screen.getByLabelText('Weight (kg)');
    expect(weightInput).toHaveValue(75.5);

    const experienceSelect = screen.getByLabelText('Experience Level');
    expect(experienceSelect).toHaveValue('intermediate');

    const goalsInput = screen.getByLabelText('Short-term Goals');
    expect(goalsInput).toHaveValue('Build muscle');
  });

  it('should cancel edit mode without saving when Cancel is clicked', () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const ageInput = screen.getByDisplayValue('30');
    fireEvent.change(ageInput, { target: { value: '35' } });

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(screen.getByRole('button', { name: /Edit Profile/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save Changes/i })).not.toBeInTheDocument();

    expect(setUserProfileMock).not.toHaveBeenCalled();
  });

  it('should save profile changes when Save is clicked', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const mockResponse = {
      id: 1,
      email: 'john@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        ...mockUserProfile,
        age: 35,
        weight_kg: 80,
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const ageInput = screen.getByDisplayValue('30');
    fireEvent.change(ageInput, { target: { value: '35' } });

    const weightInput = screen.getByDisplayValue('75.5');
    fireEvent.change(weightInput, { target: { value: '80' } });

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          age: 35,
          weight_kg: 80,
        }),
      );
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
    });

    expect(screen.getByRole('button', { name: /Edit Profile/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save Changes/i })).not.toBeInTheDocument();
  });

  it('should save profile with all fields', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const mockResponse = {
      id: 1,
      email: 'john@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: mockUserProfile,
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          age: 30,
          gender: 'male',
          weight_kg: 75.5,
          height_cm: 180,
          activity_level: 'moderately_active',
          fitness_focus: 'strength',
          experience_level: 'intermediate',
          days_per_week: 4,
          workout_duration_min: 60,
          short_term_goals: 'Build muscle',
          medium_term_goals: 'Improve overall fitness',
        }),
      );
      expect(setUserProfileMock).toHaveBeenCalled();
    });
  });

  it('should display error message when save fails', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    expect(setUserProfileMock).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
  });

  it('should dismiss error message', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const errorMessage = 'Failed to save profile';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    const dismissButton = screen.getByRole('button', { name: /Dismiss alert/i });
    fireEvent.click(dismissButton);

    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
  });

  it('should keep form in edit mode after validation error', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const errorMessage = 'Validation failed';
    vi.mocked(authApi.saveUserProfile).mockRejectedValue(new Error(errorMessage));

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const ageInput = screen.getByLabelText(/Age/i);
    fireEvent.change(ageInput, { target: { value: '99' } });

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Age/i)).toHaveValue(99);
  });

  it('should allow editing fields independently', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const mockResponse = {
      id: 1,
      email: 'john@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        ...mockUserProfile,
        short_term_goals: 'Run a 5k',
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const goalsInput = screen.getByDisplayValue('Build muscle');
    fireEvent.change(goalsInput, { target: { value: 'Run a 5k' } });

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          short_term_goals: 'Run a 5k',
        }),
      );
    });
  });

  it('should clear fields when user deletes content and saves', async () => {
    const setUserProfileMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({
        user: mockUser,
        userProfile: mockUserProfile,
        setUserProfile: setUserProfileMock,
      }),
    );

    const mockResponse = {
      id: 1,
      email: 'john@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        ...mockUserProfile,
        fitness_focus: null,
        short_term_goals: null,
      },
    };

    vi.mocked(authApi.saveUserProfile).mockResolvedValue(mockResponse);

    renderProfilePage();

    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);

    const focusSelect = screen.getByLabelText('Fitness Focus');
    fireEvent.change(focusSelect, { target: { value: '' } });

    const goalsInput = screen.getByDisplayValue('Build muscle');
    fireEvent.change(goalsInput, { target: { value: '' } });

    const saveButton = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(authApi.saveUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: null,
          short_term_goals: null,
        }),
      );
      expect(setUserProfileMock).toHaveBeenCalledWith(mockResponse.profile);
    });
  });
});
