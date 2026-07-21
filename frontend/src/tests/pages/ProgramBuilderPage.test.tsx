import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';
import * as programsApi from '@/api/programs';
import { useAuthStore } from '@/store/auth';
import type { MatchRequest } from '@/types/programCreation';

vi.mock('@/api/programs');
vi.mock('@/store/auth');

// ProgramWizardStep1's "Days per Week" control is a decorative stepper (no labeled
// input), which the tests below don't exercise - stub the whole wizard step so these
// tests can drive step 0 -> 1 with one click, independent of that form's internals.
vi.mock('@/components/ProgramWizard', () => ({
  ProgramWizard: ({ onComplete }: { onComplete: (values: MatchRequest) => void }) => (
    <button
      onClick={() =>
        onComplete({
          environment_id: 1,
          days_per_week: 3,
          session_duration_min: 60,
          weight_unit: 'kg',
          progression_style: 'consistent',
          effort_method: '',
          movement_preferences: {
            dumbbells: 50,
            barbells: 50,
            machines: 50,
            bodyweight: 50,
            cables: 50,
            kettlebells: 50,
          },
          complementary_focus: true,
          variety_preference: 'low',
        })
      }
    >
      Submit prefs
    </button>
  ),
}));

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

    fireEvent.click(screen.getByText('Submit prefs'));

    // Verify that matchTemplates was called with the user's actual fitness_focus
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: 'strength_training',
          environment_id: 1,
          days_per_week: 3,
          session_duration_min: 60,
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

    fireEvent.click(screen.getByText('Submit prefs'));

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

    fireEvent.click(screen.getByText('Submit prefs'));

    // Verify that matchTemplates was called with 'general' as fallback
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          fitness_focus: 'general',
        }),
      );
    });
  });

  describe('Details step skip UX', () => {
    beforeEach(() => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: { id: 1, email: 'test@example.com', first_name: 'John', last_name: 'Doe' },
        userProfile: { id: 1, fitness_focus: 'strength', age: 30, gender: 'male' },
        isAuthenticated: true,
        isLoading: false,
        setAuth: vi.fn(),
        setUserProfile: vi.fn(),
        clearAuth: vi.fn(),
        setLoading: vi.fn(),
      });
    });

    it('marks Details as skipped and shows an info banner when the picked template has no required inputs', async () => {
      vi.mocked(programsApi.matchTemplates).mockResolvedValue([
        {
          template_id: 1,
          slug: 'bodyweight-full-body-x3',
          name: 'Bodyweight Full Body',
          fit_pct: 80,
          factors: {},
          required_inputs: [],
          tier: 'best',
          all_infeasible: false,
          advisories: [],
        },
      ]);
      vi.mocked(programsApi.createDraft).mockResolvedValue({
        program_id: 1,
        name: 'Bodyweight Full Body',
        status: 'draft',
        duration_weeks: 8,
        weeks: { '1': [] },
        advisories: [],
      });

      render(wrap(<ProgramBuilderPage />));
      fireEvent.click(screen.getByText('Submit prefs'));

      await waitFor(() => expect(screen.getByText('Bodyweight Full Body')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Bodyweight Full Body'));

      await waitFor(() =>
        expect(screen.getByText(/This template needed no extra details/)).toBeInTheDocument(),
      );
      expect(screen.getByText('3. Details (skipped)')).toBeInTheDocument();
    });

    it('does not mark Details as skipped when the picked template has required inputs', async () => {
      vi.mocked(programsApi.matchTemplates).mockResolvedValue([
        {
          template_id: 2,
          slug: 'full-body-x3',
          name: 'Full Body',
          fit_pct: 90,
          factors: {},
          required_inputs: [
            {
              key: 'squat_start',
              label: 'Comfortable squat weight',
              type: 'number',
              applies_to: 'squat',
            },
          ],
          tier: 'best',
          all_infeasible: false,
          advisories: [],
        },
      ]);

      render(wrap(<ProgramBuilderPage />));
      fireEvent.click(screen.getByText('Submit prefs'));

      await waitFor(() => expect(screen.getByText('Full Body')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Full Body'));

      await waitFor(() =>
        expect(screen.getByLabelText('Comfortable squat weight')).toBeInTheDocument(),
      );
      expect(screen.queryByText(/\(skipped\)/)).not.toBeInTheDocument();
    });
  });
});
