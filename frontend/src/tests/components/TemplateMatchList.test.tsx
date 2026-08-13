import { it, expect, vi, describe, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateMatchList } from '@/components/TemplateMatchList';
import type { TemplateMatch } from '@/types/program';

const matches = [
  {
    template_id: 1,
    slug: 'ul',
    name: 'Upper/Lower x4',
    fit_pct: 92,
    factors: { goal: 1 },
    required_inputs: [],
    tier: 'best' as const,
    duration_weeks_default: 8,
    duration_weeks_min: 4,
    duration_weeks_max: 12,
    all_infeasible: false,
    advisories: [],
  },
  {
    template_id: 2,
    slug: 'fb',
    name: 'Full Body x3',
    fit_pct: 85,
    factors: { goal: 1 },
    required_inputs: [],
    tier: 'strong' as const,
    duration_weeks_default: 8,
    duration_weeks_min: 4,
    duration_weeks_max: 12,
    all_infeasible: false,
    advisories: [],
  },
];

const matchesInfeasible = [
  {
    template_id: 1,
    slug: 'ul',
    name: 'Upper/Lower x4',
    fit_pct: 60,
    factors: { goal: 0.6 },
    required_inputs: [],
    tier: 'possible' as const,
    duration_weeks_default: 8,
    duration_weeks_min: 4,
    duration_weeks_max: 12,
    all_infeasible: true,
    advisories: [],
  },
];

describe('TemplateMatchList', () => {
  // Existing tests
  it('renders tier badge with correct copy for "best"', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('Best match')).toBeInTheDocument();
  });

  it('renders tier badge with correct copy for "strong"', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('Strong fit')).toBeInTheDocument();
  });

  it('renders tier badge with correct copy for "possible"', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matchesInfeasible} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('Possible fit')).toBeInTheDocument();
  });

  it('renders fit % for power users (demoted)', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText(/Fit: 92%/)).toBeInTheDocument();
  });

  it('renders the duration range for each match', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.getAllByText(/Duration: 4-12 weeks/)).toHaveLength(2);
  });

  it('collapses the duration display when min equals max', () => {
    const onSelect = vi.fn();
    const fixedDurationMatch = [{ ...matches[0], duration_weeks_min: 8, duration_weeks_max: 8 }];
    render(
      <TemplateMatchList matches={fixedDurationMatch} selectedId={null} onSelect={onSelect} />,
    );
    expect(screen.getByText(/Duration: 8 weeks/)).toBeInTheDocument();
  });

  it('selects on click', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button', { name: /Upper\/Lower x4/ }));
    expect(onSelect).toHaveBeenCalledWith(matches[0]);
  });

  it('shows all-infeasible warning when all_infeasible is true', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matchesInfeasible} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('No perfect match found')).toBeInTheDocument();
    expect(
      screen.getByText(/None of your available templates fully match your setup/),
    ).toBeInTheDocument();
  });

  it('does not show all-infeasible warning when all_infeasible is false', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    expect(screen.queryByText('No perfect match found')).not.toBeInTheDocument();
  });

  it('renders empty state when no matches', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={[]} selectedId={null} onSelect={onSelect} />);
    expect(screen.getByText('No matching templates for your setup.')).toBeInTheDocument();
  });

  it('renders per-template advisories with correct severity', () => {
    const onSelect = vi.fn();
    const matchesWithAdvisories = [
      {
        template_id: 1,
        slug: 'ul',
        name: 'Upper/Lower x4',
        fit_pct: 92,
        factors: { goal: 1 },
        required_inputs: [],
        tier: 'best' as const,
        duration_weeks_default: 8,
        duration_weeks_min: 4,
        duration_weeks_max: 12,
        all_infeasible: false,
        advisories: [
          {
            code: 'freq-low',
            severity: 'warning' as const,
            message: 'Chest training frequency is below MEV for hypertrophy.',
            subject: 'chest',
          },
        ],
      },
    ];
    render(
      <TemplateMatchList matches={matchesWithAdvisories} selectedId={null} onSelect={onSelect} />,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(
      screen.getByText('Chest training frequency is below MEV for hypertrophy.'),
    ).toBeInTheDocument();
  });

  it('does not render advisories when array is empty', () => {
    const onSelect = vi.fn();
    render(<TemplateMatchList matches={matches} selectedId={null} onSelect={onSelect} />);
    const alerts = screen.queryAllByRole('alert');
    expect(alerts).toHaveLength(0);
  });

  // Load more button tests (new)
  describe('Load More Button', () => {
    afterEach(() => {
      vi.clearAllMocks();
    });

    // Helper to render with load more props
    const renderWithLoadMore = (props: any): ReturnType<typeof render> => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      return render((<TemplateMatchList {...props} />) as any);
    };

    it('renders all matches passed in array', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      expect(screen.getByText('Upper/Lower x4')).toBeInTheDocument();
      expect(screen.getByText('Full Body x3')).toBeInTheDocument();
    });

    it('renders "Load more" button when hasMore is true', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      const loadMoreButton = screen.getByRole('button', { name: /Load more/ });
      expect(loadMoreButton).toBeInTheDocument();
    });

    it('shows loading spinner when isLoading is true', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: true,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      const spinner = screen.getByTestId('loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('shows "No more matches available" message when no more and not loading', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore: vi.fn(),
      });

      expect(screen.getByText('No more matches available')).toBeInTheDocument();
    });

    it('does not show "No more matches" while loading', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: true,
        hasMore: false,
        onLoadMore: vi.fn(),
      });

      expect(screen.queryByText('No more matches available')).not.toBeInTheDocument();
    });

    it('does not show "No more matches" when matches are empty', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches: [],
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore: vi.fn(),
      });

      expect(screen.queryByText('No more matches available')).not.toBeInTheDocument();
    });

    it('shows "Load more" button when hasMore is true', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      const loadMoreButton = screen.getByRole('button', { name: /Load more/ });
      expect(loadMoreButton).toBeInTheDocument();
    });

    it('calls onLoadMore when "Load more" button is clicked', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore,
      });

      const loadMoreButton = screen.getByRole('button', { name: /Load more/ });
      fireEvent.click(loadMoreButton);

      expect(onLoadMore).toHaveBeenCalled();
    });

    it('shows loading spinner while isLoading is true', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: true,
        hasMore: true,
        onLoadMore,
      });

      const spinner = screen.getByTestId('loading-spinner');
      expect(spinner).toBeInTheDocument();
      const loadMoreButton = screen.queryByRole('button', { name: /Load more/ });
      expect(loadMoreButton).not.toBeInTheDocument();
    });

    it('does not show "Load more" button when hasMore is false', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore,
      });

      const loadMoreButton = screen.queryByRole('button', { name: /Load more/ });
      expect(loadMoreButton).not.toBeInTheDocument();
    });

    it('handles empty matches with infinite scroll props', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches: [],
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      expect(screen.getByText('No matching templates for your setup.')).toBeInTheDocument();
    });

    it('allows selection on paginated matches', () => {
      const onSelect = vi.fn();
      const paginatedMatches: TemplateMatch[] = [
        ...matches,
        {
          template_id: 3,
          slug: 'ppl',
          name: 'Push/Pull/Legs',
          fit_pct: 78,
          factors: { goal: 1 },
          required_inputs: [],
          tier: 'strong' as const,
          duration_weeks_default: 8,
          duration_weeks_min: 4,
          duration_weeks_max: 12,
          all_infeasible: false,
          advisories: [],
        },
      ];

      renderWithLoadMore({
        matches: paginatedMatches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      fireEvent.click(screen.getByRole('button', { name: /Push\/Pull\/Legs/ }));
      expect(onSelect).toHaveBeenCalledWith(paginatedMatches[2]);
    });

    it('shows warning alert for infeasible matches with infinite scroll', () => {
      const onSelect = vi.fn();
      renderWithLoadMore({
        matches: matchesInfeasible,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore: vi.fn(),
      });

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('No perfect match found')).toBeInTheDocument();
    });
  });
});
