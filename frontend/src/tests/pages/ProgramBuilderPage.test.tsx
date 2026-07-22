import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';
import * as programsApi from '@/api/programs';
import * as trainingEnvironmentsApi from '@/api/trainingEnvironments';
import { useAuthStore } from '@/store/auth';
import type { MatchRequest } from '@/types/programCreation';

vi.mock('@/api/programs');
vi.mock('@/api/trainingEnvironments');
vi.mock('@/store/auth');

// ProgramWizardStep1's "Days per Week" control is a decorative stepper (no labeled
// input), which the tests below don't exercise - stub the whole wizard step so these
// tests can drive step 0 -> 1 with one click, independent of that form's internals.
// onComplete echoes back whatever environmentId the page resolved and passed down, so
// tests can verify the resolution logic without exercising the real form.
vi.mock('@/components/ProgramWizard', () => ({
  ProgramWizard: ({
    environmentId,
    onComplete,
  }: {
    environmentId: number;
    onComplete: (values: MatchRequest) => void;
  }) => (
    <button
      onClick={() =>
        onComplete({
          environment_id: environmentId,
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
let mockParams: { environmentId?: string } = { environmentId: '1' };
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

function wrap(ui: React.ReactNode) {
  return (
    <BrowserRouter>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </BrowserRouter>
  );
}

const mockTemplateMatchResponse = (matches: any[] = []) => ({
  matches,
  total_count: matches.length,
  offset: 0,
  limit: 10,
});

describe('ProgramBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParams = { environmentId: '1' };
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

    vi.mocked(programsApi.matchTemplates).mockResolvedValue(mockTemplateMatchResponse());

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

    vi.mocked(programsApi.matchTemplates).mockResolvedValue(mockTemplateMatchResponse());

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

    vi.mocked(programsApi.matchTemplates).mockResolvedValue(mockTemplateMatchResponse());

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
      vi.mocked(programsApi.matchTemplates).mockResolvedValue(
        mockTemplateMatchResponse([
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
        ]),
      );
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
      vi.mocked(programsApi.matchTemplates).mockResolvedValue(
        mockTemplateMatchResponse([
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
        ]),
      );

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

  describe('resolving the environment when no route param is given', () => {
    beforeEach(() => {
      mockParams = {};
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

    it('shows a prompt to create an environment instead of guessing an id, when the user has none', async () => {
      vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([]);

      render(wrap(<ProgramBuilderPage />));

      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: /add a training environment/i }),
        ).toBeInTheDocument(),
      );
      expect(screen.queryByText('Submit prefs')).not.toBeInTheDocument();
    });

    it('auto-selects the only environment when exactly one exists', async () => {
      vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([
        { id: 42, name: 'Home', environment_type: 'home', equipment_tags: [], is_default: false },
      ]);
      vi.mocked(programsApi.matchTemplates).mockResolvedValue(mockTemplateMatchResponse());

      render(wrap(<ProgramBuilderPage />));

      await waitFor(() => expect(screen.getByText('Submit prefs')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Submit prefs'));

      await waitFor(() =>
        expect(programsApi.matchTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ environment_id: 42 }),
        ),
      );
    });

    it('prefers the default environment when several exist', async () => {
      vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([
        {
          id: 5,
          name: 'Gym',
          environment_type: 'commercial_gym',
          equipment_tags: [],
          is_default: false,
        },
        { id: 9, name: 'Home', environment_type: 'home', equipment_tags: [], is_default: true },
      ]);
      vi.mocked(programsApi.matchTemplates).mockResolvedValue(mockTemplateMatchResponse());

      render(wrap(<ProgramBuilderPage />));

      await waitFor(() => expect(screen.getByText('Submit prefs')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Submit prefs'));

      await waitFor(() =>
        expect(programsApi.matchTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ environment_id: 9 }),
        ),
      );
    });
  });
});
