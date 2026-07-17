import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';
import * as programsApi from '@/api/programs';
import { useAuthStore } from '@/store/auth';

vi.mock('@/api/programs');
vi.mock('@/store/auth');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ environmentId: '1' }),
  };
});

function wrap(ui: React.ReactNode) {
  return (
    <BrowserRouter>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </BrowserRouter>
  );
}

describe('ProgramBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should include user fitness_focus in match request instead of hardcoded value', async () => {
    const userProfileWithFitnessFocus = {
      id: 1,
      fitness_focus: 'strength_training',
      age: 30,
      gender: 'male',
    };

    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
      userProfile: userProfileWithFitnessFocus,
      isAuthenticated: true,
      isLoading: false,
      setAuth: vi.fn(),
      setUserProfile: vi.fn(),
      clearAuth: vi.fn(),
      setLoading: vi.fn(),
    });

    vi.mocked(programsApi.matchTemplates).mockResolvedValue([]);

    render(wrap(<ProgramBuilderPage />));

    // Wait for form to render
    await waitFor(() => {
      expect(screen.getByLabelText(/Days per Week/i)).toBeInTheDocument();
    });

    // Fill in form and submit
    fireEvent.change(screen.getByLabelText(/Days per Week/i), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText(/Session Duration/i), {
      target: { value: '45' },
    });
    fireEvent.change(screen.getByLabelText(/Weight Unit/i), {
      target: { value: 'kg' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    // Verify that matchTemplates was called with the user's actual fitness_focus
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: 'strength_training',
          environment_id: 1,
          days_per_week: 4,
          session_duration_min: 45,
          weight_unit: 'kg',
          duration_weeks: 8,
        }),
      );
    });
  });

  it('should use general as fallback fitness_focus when userProfile is null', async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
      userProfile: null,
      isAuthenticated: true,
      isLoading: false,
      setAuth: vi.fn(),
      setUserProfile: vi.fn(),
      clearAuth: vi.fn(),
      setLoading: vi.fn(),
    });

    vi.mocked(programsApi.matchTemplates).mockResolvedValue([]);

    render(wrap(<ProgramBuilderPage />));

    // Wait for form to render
    await waitFor(() => {
      expect(screen.getByLabelText(/Days per Week/i)).toBeInTheDocument();
    });

    // Fill in form and submit
    fireEvent.change(screen.getByLabelText(/Days per Week/i), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText(/Session Duration/i), {
      target: { value: '45' },
    });
    fireEvent.change(screen.getByLabelText(/Weight Unit/i), {
      target: { value: 'kg' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    // Verify that matchTemplates was called with 'general' as fallback
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: 'general',
        }),
      );
    });
  });

  it('should use general as fallback fitness_focus when userProfile.fitness_focus is null', async () => {
    const userProfileWithoutFitnessFocus = {
      id: 1,
      fitness_focus: null,
      age: 30,
      gender: 'male',
    };

    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
      userProfile: userProfileWithoutFitnessFocus,
      isAuthenticated: true,
      isLoading: false,
      setAuth: vi.fn(),
      setUserProfile: vi.fn(),
      clearAuth: vi.fn(),
      setLoading: vi.fn(),
    });

    vi.mocked(programsApi.matchTemplates).mockResolvedValue([]);

    render(wrap(<ProgramBuilderPage />));

    // Wait for form to render
    await waitFor(() => {
      expect(screen.getByLabelText(/Days per Week/i)).toBeInTheDocument();
    });

    // Fill in form and submit
    fireEvent.change(screen.getByLabelText(/Days per Week/i), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText(/Session Duration/i), {
      target: { value: '45' },
    });
    fireEvent.change(screen.getByLabelText(/Weight Unit/i), {
      target: { value: 'kg' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    // Verify that matchTemplates was called with 'general' as fallback
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: 'general',
        }),
      );
    });
  });
});
