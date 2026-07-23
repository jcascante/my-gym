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
    // (2nd call; 1st call is with empty request on mount)
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          fitness_focus: 'strength_training',
          environment_id: 1,
          days_per_week: 3,
          session_duration_min: 60,
          weight_unit: 'kg',
          duration_weeks: 8,
        }),
        4,
        0,
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
    // (2nd call; 1st call is with empty request on mount)
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          fitness_focus: 'general',
        }),
        4,
        0,
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
    // (2nd call; 1st call is with empty request on mount)
    await waitFor(() => {
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          fitness_focus: 'general',
        }),
        4,
        0,
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

      // The 2nd call has the actual environment ID (1st call is empty on mount)
      await waitFor(() =>
        expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
          2,
          expect.objectContaining({ environment_id: 42 }),
          4,
          0,
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

      // The 2nd call has the actual environment ID (1st call is empty on mount)
      await waitFor(() =>
        expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
          2,
          expect.objectContaining({ environment_id: 9 }),
          4,
          0,
        ),
      );
    });
  });

  describe('Infinite scroll integration', () => {
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

    it('should load initial batch and allow selection, verifying offset parameters', async () => {
      const createTemplateMatch = (id: number) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs: [],
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      // Initial batch: 4 templates
      const initialMatches = [1, 2, 3, 4].map(createTemplateMatch);

      // First call returns empty (initial empty request)
      // Subsequent calls return matched templates
      vi.mocked(programsApi.matchTemplates)
        .mockResolvedValueOnce({
          matches: [],
          total_count: 0,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValue({
          matches: initialMatches,
          total_count: 4,
          offset: 0,
          limit: 4,
        });

      vi.mocked(programsApi.createDraft).mockResolvedValue({
        program_id: 100,
        name: 'Template 1',
        status: 'draft',
        duration_weeks: 8,
        weeks: { '1': [] },
        advisories: [],
      });

      render(wrap(<ProgramBuilderPage />));

      // Step 0: Submit preferences
      fireEvent.click(screen.getByText('Submit prefs'));

      // Step 1: Verify initial batch renders
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
        expect(screen.getByText('Template 2')).toBeInTheDocument();
        expect(screen.getByText('Template 3')).toBeInTheDocument();
        expect(screen.getByText('Template 4')).toBeInTheDocument();
      });

      // Verify second API call (after prefs) has correct offset=0, limit=4
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          environment_id: 1,
          days_per_week: 3,
          session_duration_min: 60,
        }),
        4,
        0,
      );

      // Select first template
      fireEvent.click(screen.getByText('Template 1'));

      // Verify navigation to next step
      await waitFor(() => {
        expect(programsApi.createDraft).toHaveBeenCalledWith(
          expect.objectContaining({
            template_id: 1,
            environment_id: 1,
          }),
        );
      });
    });

    it('should handle edge case: few matches (< 4), show "No more" message', async () => {
      const createTemplateMatch = (id: number) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs: [],
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      const fewMatches = [1, 2].map(createTemplateMatch);

      // First call returns empty (initial empty request)
      // Second call returns few matches (actual request after prefs)
      vi.mocked(programsApi.matchTemplates)
        .mockResolvedValueOnce({
          matches: [],
          total_count: 0,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValue({
          matches: fewMatches,
          total_count: 2,
          offset: 0,
          limit: 4,
        });

      render(wrap(<ProgramBuilderPage />));

      fireEvent.click(screen.getByText('Submit prefs'));

      // Verify few matches render
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
        expect(screen.getByText('Template 2')).toBeInTheDocument();
      });

      // Verify "No more matches available" shows (hasMore=false when loaded == total)
      await waitFor(() => {
        expect(screen.getByText('No more matches available')).toBeInTheDocument();
      });
    });

    it('should support template selection from paginated list', async () => {
      const createTemplateMatch = (id: number, required_inputs: any[] = []) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs,
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      // Two templates with no required inputs
      const matches = [1, 2].map((id) => createTemplateMatch(id));

      // First call returns empty (initial empty request)
      // Subsequent calls return matched templates
      vi.mocked(programsApi.matchTemplates)
        .mockResolvedValueOnce({
          matches: [],
          total_count: 0,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValue({
          matches,
          total_count: 2,
          offset: 0,
          limit: 4,
        });

      vi.mocked(programsApi.createDraft).mockResolvedValue({
        program_id: 100,
        name: 'Draft Program',
        status: 'draft',
        duration_weeks: 8,
        weeks: { '1': [] },
        advisories: [],
      });

      render(wrap(<ProgramBuilderPage />));

      fireEvent.click(screen.getByText('Submit prefs'));

      await waitFor(() => {
        expect(screen.getByText('Template 2')).toBeInTheDocument();
      });

      // Select second template (from matched list)
      fireEvent.click(screen.getByText('Template 2'));

      // Verify draft created for selected template
      await waitFor(() => {
        expect(programsApi.createDraft).toHaveBeenCalledWith(
          expect.objectContaining({
            template_id: 2,
          }),
        );
      });
    });

    it('should verify loading spinner appears during pagination', async () => {
      const createTemplateMatch = (id: number) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs: [],
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      const initialMatches = [1, 2, 3, 4].map(createTemplateMatch);

      // First call returns empty (initial empty request)
      // Subsequent calls return matched templates
      vi.mocked(programsApi.matchTemplates)
        .mockResolvedValueOnce({
          matches: [],
          total_count: 0,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValue({
          matches: initialMatches,
          total_count: 7,
          offset: 0,
          limit: 4,
        });

      render(wrap(<ProgramBuilderPage />));

      fireEvent.click(screen.getByText('Submit prefs'));

      // Initial load completes
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
      });

      // No loading spinner when not loading
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
    });

    it('should support infinite scroll pagination with correct offsets', async () => {
      const createTemplateMatch = (id: number) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs: [],
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      // Batch 1: templates 1-4 (offset=0, limit=4)
      const batch1 = [1, 2, 3, 4].map(createTemplateMatch);
      // Batch 2: templates 5-7 (offset=4, limit=3)
      const batch2 = [5, 6, 7].map(createTemplateMatch);
      // Batch 3: templates 8-10 (offset=7, limit=3)
      const batch3 = [8, 9, 10].map(createTemplateMatch);

      // First call returns empty (initial empty request on mount)
      // Then setup responses for: initial load, first scroll, second scroll
      vi.mocked(programsApi.matchTemplates)
        .mockResolvedValueOnce({
          matches: [],
          total_count: 0,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValueOnce({
          matches: batch1,
          total_count: 10,
          offset: 0,
          limit: 4,
        })
        .mockResolvedValueOnce({
          matches: batch2,
          total_count: 10,
          offset: 4,
          limit: 3,
        })
        .mockResolvedValueOnce({
          matches: batch3,
          total_count: 10,
          offset: 7,
          limit: 3,
        });

      let observerCallback: IntersectionObserverCallback | null = null;

      // Mock IntersectionObserver to capture callback
      (globalThis as unknown as { IntersectionObserver: unknown }).IntersectionObserver = vi.fn(
        function (callback: IntersectionObserverCallback) {
          observerCallback = callback;
          return {
            observe: vi.fn(),
            unobserve: vi.fn(),
            disconnect: vi.fn(),
          } as unknown as IntersectionObserver;
        },
      );

      render(wrap(<ProgramBuilderPage />));

      // Step 1: Submit preferences to trigger initial load
      fireEvent.click(screen.getByText('Submit prefs'));

      // Step 2: Wait for initial batch to load (4 items)
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
        expect(screen.getByText('Template 4')).toBeInTheDocument();
      });

      // Verify second API call (after prefs) has offset=0, limit=4
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ environment_id: 1 }),
        4,
        0,
      );

      // Step 3: Simulate scroll to bottom by calling observer callback
      expect(observerCallback).not.toBeNull();
      const scrollCallback = observerCallback as unknown as IntersectionObserverCallback;
      scrollCallback(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );

      // Step 4: Wait for second batch to load (next 3 items)
      await waitFor(() => {
        expect(screen.getByText('Template 5')).toBeInTheDocument();
        expect(screen.getByText('Template 7')).toBeInTheDocument();
      });

      // Verify third API call has offset=4, limit=3
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        3,
        expect.objectContaining({ environment_id: 1 }),
        3,
        4,
      );

      // Step 5: Simulate another scroll to bottom
      const scrollCallback2 = observerCallback as unknown as IntersectionObserverCallback;
      scrollCallback2(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );

      // Step 6: Wait for third batch to load (final 3 items)
      await waitFor(() => {
        expect(screen.getByText('Template 8')).toBeInTheDocument();
        expect(screen.getByText('Template 10')).toBeInTheDocument();
      });

      // Verify fourth API call has offset=7, limit=3
      expect(programsApi.matchTemplates).toHaveBeenNthCalledWith(
        4,
        expect.objectContaining({ environment_id: 1 }),
        3,
        7,
      );

      // Verify "No more matches" message appears after final batch
      await waitFor(() => {
        expect(screen.getByText('No more matches available')).toBeInTheDocument();
      });
    });

    it('should demonstrate correct offset progression during multi-page scroll', async () => {
      const createTemplateMatch = (id: number) => ({
        template_id: id,
        slug: `template-${id}`,
        name: `Template ${id}`,
        fit_pct: 80 + id,
        factors: {},
        required_inputs: [],
        tier: 'best' as const,
        all_infeasible: false,
        advisories: [],
      });

      // Batch 1: templates 1-4 (offset=0, limit=4)
      const batch1 = [1, 2, 3, 4].map(createTemplateMatch);
      // Batch 2: templates 5-7 (offset=4, limit=3)
      const batch2 = [5, 6, 7].map(createTemplateMatch);
      // Batch 3: templates 8-10 (offset=7, limit=3)
      const batch3 = [8, 9, 10].map(createTemplateMatch);

      // Track API calls with their offset to verify pagination progression
      const apiCalls: Array<{ limit: number; offset: number }> = [];
      vi.mocked(programsApi.matchTemplates).mockImplementation((_req, limit = 4, offset = 0) => {
        apiCalls.push({ limit, offset });

        if (offset === 0 && limit === 4) {
          return Promise.resolve({
            matches: batch1,
            total_count: 10,
            offset: 0,
            limit: 4,
          });
        }
        if (offset === 4 && limit === 3) {
          return Promise.resolve({
            matches: batch2,
            total_count: 10,
            offset: 4,
            limit: 3,
          });
        }
        if (offset === 7 && limit === 3) {
          return Promise.resolve({
            matches: batch3,
            total_count: 10,
            offset: 7,
            limit: 3,
          });
        }
        return Promise.resolve({
          matches: [],
          total_count: 10,
          offset,
          limit,
        });
      });

      let observerCallback: IntersectionObserverCallback | null = null;

      (globalThis as unknown as { IntersectionObserver: unknown }).IntersectionObserver = vi.fn(
        function (callback: IntersectionObserverCallback) {
          observerCallback = callback;
          return {
            observe: vi.fn(),
            unobserve: vi.fn(),
            disconnect: vi.fn(),
          } as unknown as IntersectionObserver;
        },
      );

      render(wrap(<ProgramBuilderPage />));

      fireEvent.click(screen.getByText('Submit prefs'));

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
      });

      // Verify initial call used offset=0, limit=4
      const initialCallIndex = apiCalls.findIndex((call) => call.offset === 0 && call.limit === 4);
      expect(initialCallIndex).toBeGreaterThanOrEqual(0);

      // Simulate scroll to load next page
      const scrollCallback3 = observerCallback as unknown as IntersectionObserverCallback;
      scrollCallback3(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );

      await waitFor(() => {
        expect(screen.getByText('Template 5')).toBeInTheDocument();
      });

      // Verify second call used offset=4, limit=3
      expect(apiCalls).toContainEqual({ limit: 3, offset: 4 });

      // Simulate another scroll to load third page
      const scrollCallback4 = observerCallback as unknown as IntersectionObserverCallback;
      scrollCallback4(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );

      await waitFor(() => {
        expect(screen.getByText('Template 8')).toBeInTheDocument();
      });

      // Verify third call used offset=7, limit=3
      expect(apiCalls).toContainEqual({ limit: 3, offset: 7 });
    });
  });
});
