import { it, expect, vi, describe, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateMatchList } from '@/components/TemplateMatchList';
import type { TemplateMatch } from '@/types/program';

// Type for IntersectionObserver callback
type IOCallback = (entries: IntersectionObserverEntry[]) => void;

const matches = [
  {
    template_id: 1,
    slug: 'ul',
    name: 'Upper/Lower x4',
    fit_pct: 92,
    factors: { goal: 1 },
    required_inputs: [],
    tier: 'best' as const,
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

  // Infinite scroll tests (new)
  describe('Infinite Scroll', () => {
    let observerCallback: IOCallback | null = null;
    let mockObserver: {
      observe: ReturnType<typeof vi.fn>;
      unobserve: ReturnType<typeof vi.fn>;
      disconnect: ReturnType<typeof vi.fn>;
    };

    beforeEach(() => {
      observerCallback = null;
      mockObserver = {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      };

      const IntersectionObserverMock = vi.fn((callback: IOCallback) => {
        observerCallback = callback;
        return mockObserver;
      });

      (globalThis as any).IntersectionObserver = IntersectionObserverMock;
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    // Helper to render with infinite scroll props (component will have these in Task 5)
    const renderWithInfiniteScroll = (props: any): ReturnType<typeof render> => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      return render((<TemplateMatchList {...props} />) as any);
    };

    it('renders all matches passed in array', () => {
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
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

    it('renders invisible sentinel element with test id', () => {
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      const sentinel = screen.getByTestId('template-match-sentinel');
      expect(sentinel).toBeInTheDocument();
      expect(sentinel).toHaveStyle({ height: '1px' });
    });

    it('shows loading spinner when isLoading is true', () => {
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
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
      renderWithInfiniteScroll({
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
      renderWithInfiniteScroll({
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
      renderWithInfiniteScroll({
        matches: [],
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore: vi.fn(),
      });

      expect(screen.queryByText('No more matches available')).not.toBeInTheDocument();
    });

    it('attaches IntersectionObserver to sentinel element', () => {
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore: vi.fn(),
      });

      expect(globalThis.IntersectionObserver as any).toHaveBeenCalled();
      expect(mockObserver.observe).toHaveBeenCalled();
    });

    it('calls onLoadMore when sentinel intersects with proper conditions', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: true,
        onLoadMore,
      });

      if (observerCallback) {
        observerCallback([{ isIntersecting: true } as IntersectionObserverEntry]);
      }

      expect(onLoadMore).toHaveBeenCalled();
    });

    it('does not call onLoadMore while isLoading is true', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
        matches,
        selectedId: null,
        onSelect,
        isLoading: true,
        hasMore: true,
        onLoadMore,
      });

      if (observerCallback) {
        observerCallback([{ isIntersecting: true } as IntersectionObserverEntry]);
      }

      expect(onLoadMore).not.toHaveBeenCalled();
    });

    it('does not call onLoadMore when hasMore is false', () => {
      const onLoadMore = vi.fn();
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
        matches,
        selectedId: null,
        onSelect,
        isLoading: false,
        hasMore: false,
        onLoadMore,
      });

      if (observerCallback) {
        observerCallback([{ isIntersecting: true } as IntersectionObserverEntry]);
      }

      expect(onLoadMore).not.toHaveBeenCalled();
    });

    it('handles empty matches with infinite scroll props', () => {
      const onSelect = vi.fn();
      renderWithInfiniteScroll({
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
          all_infeasible: false,
          advisories: [],
        },
      ];

      renderWithInfiniteScroll({
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
      renderWithInfiniteScroll({
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
