import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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

function wrap(ui: React.ReactNode) {
  return (
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

async function submitProgramCreationForm(user: ReturnType<typeof userEvent.setup>) {
  fireEvent.change(screen.getByLabelText(/Days per Week/i), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText(/Session Duration/i), { target: { value: '60' } });
  fireEvent.change(screen.getByLabelText(/Weight Unit/i), { target: { value: 'kg' } });
  await user.click(screen.getByRole('button', { name: /Next/i }));
}

describe('ProgramBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('advances from preferences to template selection', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);

    expect(await screen.findByText('Full Body')).toBeInTheDocument();
  });

  it('submits preferences to move forward', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);

    expect(await screen.findByText('Full Body')).toBeInTheDocument();
  });

  it('shows Back button on step 1 (template selection)', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);

    expect(await screen.findByText('Back')).toBeInTheDocument();
  });

  it('navigates back from step 1 to step 0', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);
    await screen.findByText('Full Body');

    await user.click(screen.getByText('Back'));

    expect(screen.getByLabelText(/Days per Week/i)).toBeInTheDocument();
  });

  it('preserves preferences when navigating backward', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);
    await screen.findByText('Full Body');

    await user.click(screen.getByText('Back'));

    expect(screen.getByLabelText(/Days per Week/i)).toHaveValue(3);
    expect(screen.getByLabelText(/Session Duration/i)).toHaveValue(60);
    expect(screen.getByLabelText(/Weight Unit/i)).toHaveValue('kg');
  });

  it('shows Accept button on step 3 (review)', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);
    await screen.findByText('Full Body');

    await user.click(screen.getByText('Full Body'));

    expect(await screen.findByText('Accept program')).toBeInTheDocument();
  });

  it('shows Back button on step 3 (review)', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);
    await screen.findByText('Full Body');

    await user.click(screen.getByText('Full Body'));

    expect(await screen.findByText('Back')).toBeInTheDocument();
  });

  it('navigates back from step 3 to step 1 when template has no required inputs', async () => {
    const user = userEvent.setup();
    render(wrap(<ProgramBuilderPage />));

    await submitProgramCreationForm(user);
    await screen.findByText('Full Body');

    await user.click(screen.getByText('Full Body'));
    await screen.findByText('Accept program');

    await user.click(screen.getByText('Back'));

    expect(screen.getByText('Full Body')).toBeInTheDocument();
  });
});
