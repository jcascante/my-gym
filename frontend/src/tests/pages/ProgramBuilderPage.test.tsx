import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProgramBuilderPage from '@/pages/ProgramBuilderPage';

const match = {
  template_id: 1,
  slug: 'fb',
  name: 'Full Body',
  fit_pct: 90,
  factors: {},
  required_inputs: [],
};

vi.mock('@/hooks/usePrograms', () => ({
  useMatchTemplates: () => ({
    mutate: (_: unknown, options: { onSuccess: (data: (typeof match)[]) => void }) =>
      options.onSuccess([match]),
    data: [match],
    isPending: false,
  }),
  useCreateDraft: () => ({
    mutateAsync: vi.fn().mockResolvedValue({
      program_id: 1,
      name: 'Draft',
      status: 'draft' as const,
      duration_weeks: 8,
      weeks: {},
    }),
    isPending: false,
  }),
  useProgramPreview: () => ({ data: undefined }),
  useSubmitFeedback: () => ({ mutate: vi.fn() }),
  useAcceptProgram: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ program_id: 1 }),
  }),
  useSlotAlternatives: () => ({ data: [] }),
  programKeys: { preview: (id: number) => ['program', id] },
}));

interface MockProgramCreationFormProps {
  onSubmit: (values: {
    environment_id: number;
    days_per_week: number;
    session_duration_min: number;
    weight_unit: string;
  }) => void;
}

vi.mock('@/components/ProgramCreationForm', () => ({
  ProgramCreationForm: ({ onSubmit }: MockProgramCreationFormProps) => (
    <button
      onClick={() =>
        onSubmit({
          environment_id: 1,
          days_per_week: 3,
          session_duration_min: 60,
          weight_unit: 'kg',
        })
      }
    >
      go
    </button>
  ),
}));

function wrap(ui: React.ReactNode) {
  return (
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe('ProgramBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('advances from preferences to template selection', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await user.click(screen.getByText('go'));

    expect(await screen.findByText('Full Body')).toBeInTheDocument();
  });
});
