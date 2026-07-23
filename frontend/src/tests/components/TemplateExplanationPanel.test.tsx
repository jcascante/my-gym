import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TemplateExplanationPanel } from '@/components/TemplateExplanationPanel';
import type { TemplateExplanation } from '@/types/explain';

let explanationState: {
  data: TemplateExplanation | undefined;
  isLoading: boolean;
  isError: boolean;
} = {
  data: undefined,
  isLoading: false,
  isError: false,
};

vi.mock('@/hooks/useExplain', () => ({
  useTemplateExplanation: () => explanationState,
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  explanationState = { data: undefined, isLoading: false, isError: false };
});

it('starts collapsed, showing only the toggle', () => {
  render(wrap(<TemplateExplanationPanel programId={1} />));
  expect(screen.getByText('Why this template?')).toBeInTheDocument();
  expect(screen.queryByText(/fit/)).not.toBeInTheDocument();
});

it('shows a spinner while loading after expanding', () => {
  explanationState = { data: undefined, isLoading: true, isError: false };
  render(wrap(<TemplateExplanationPanel programId={1} />));
  fireEvent.click(screen.getByText('Why this template?'));
  expect(screen.getByText('Hide why this template')).toBeInTheDocument();
});

it('renders fit_pct, tier, factors, and advisories once loaded', () => {
  explanationState = {
    data: {
      template_id: 1,
      slug: 'full-body-x3',
      name: 'Full Body',
      fit_pct: 92,
      factors: { goal: 1.0, experience: 0.5 },
      tier: 'best',
      advisories: [
        {
          code: 'FREQUENCY_STRUCTURALLY_LIMITED',
          severity: 'info',
          message: 'Low frequency.',
          subject: 'chest',
        },
      ],
    },
    isLoading: false,
    isError: false,
  };
  render(wrap(<TemplateExplanationPanel programId={1} />));
  fireEvent.click(screen.getByText('Why this template?'));

  expect(screen.getByText(/92% fit/)).toBeInTheDocument();
  expect(screen.getByText(/Best match/)).toBeInTheDocument();
  expect(screen.getByText('goal')).toBeInTheDocument();
  expect(screen.getByText('100%')).toBeInTheDocument();
  expect(screen.getByText('Low frequency.')).toBeInTheDocument();
});

it('shows an error message when the explanation fails to load', () => {
  explanationState = { data: undefined, isLoading: false, isError: true };
  render(wrap(<TemplateExplanationPanel programId={1} />));
  fireEvent.click(screen.getByText('Why this template?'));
  expect(screen.getByText(/Couldn't load an explanation/)).toBeInTheDocument();
});
