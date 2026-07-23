import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TemplatesPage from '@/pages/TemplatesPage';
import * as templatesApi from '@/api/templates';
import type { Template } from '@/types/template';

vi.mock('@/api/templates');

const mockTemplate: Template = {
  slug: 'full-body-x3',
  name: 'Full Body 3x/Week',
  description: 'Three full-body days for beginners building general strength.',
  goals: ['general', 'strength'],
  experience_levels: ['beginner'],
  days_per_week_min: 3,
  days_per_week_max: 3,
  session_duration_min: 45,
  session_duration_max: 60,
  split: {
    sessions: [
      {
        key: 'full_a',
        name: 'Full Body A',
        order: 1,
        slots: [{ pattern: 'squat', priority: 'primary', scheme: 'main' }],
      },
    ],
    schemes: {
      main: {
        sets: 3,
        reps_min: 5,
        reps_max: 5,
        rest_seconds: 120,
        target_rpe: 8.0,
        intensity_pct: 0.8,
      },
    },
  },
  progression_ref: { model_key: 'linear_load', params: { increment: 2.5 }, deload_every: 4 },
  required_inputs: [],
};

const mockTemplate2: Template = {
  ...mockTemplate,
  slug: 'ppl-x6',
  name: 'Push/Pull/Legs 6x/Week',
  description: 'Six days split across push, pull, and legs for intermediate lifters.',
};

function renderPage() {
  render(
    <BrowserRouter>
      <TemplatesPage />
    </BrowserRouter>,
  );
}

describe('TemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading spinner on initial load', () => {
    vi.mocked(templatesApi.listTemplates).mockImplementation(() => new Promise(() => {}));

    renderPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should fetch and render templates on mount', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    });
  });

  it('should render multiple templates', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate, mockTemplate2]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
      expect(screen.getByText('Push/Pull/Legs 6x/Week')).toBeInTheDocument();
    });
  });

  it('should expand template when clicked', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));

    await waitFor(() => {
      expect(
        screen.getByText('Three full-body days for beginners building general strength.'),
      ).toBeInTheDocument();
    });
  });

  it('should collapse template when clicked again', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(
        screen.getByText('Three full-body days for beginners building general strength.'),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(
        screen.queryByText('Three full-body days for beginners building general strength.'),
      ).not.toBeInTheDocument();
    });
  });

  it('should only allow one template expanded at a time', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([mockTemplate, mockTemplate2]);

    renderPage();

    await waitFor(() => screen.getByText('Full Body 3x/Week'));

    fireEvent.click(screen.getByText('Full Body 3x/Week'));
    await waitFor(() => {
      expect(
        screen.getByText('Three full-body days for beginners building general strength.'),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Push/Pull/Legs 6x/Week'));
    await waitFor(() => {
      expect(
        screen.queryByText('Three full-body days for beginners building general strength.'),
      ).not.toBeInTheDocument();
    });
  });

  it('should show error alert on fetch failure', async () => {
    vi.mocked(templatesApi.listTemplates).mockRejectedValue(new Error('Failed to load templates'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Failed to load templates/i)).toBeInTheDocument();
    });
  });

  it('should retry fetching templates when retry button clicked', async () => {
    vi.mocked(templatesApi.listTemplates)
      .mockRejectedValueOnce(new Error('Failed to load templates'))
      .mockResolvedValueOnce([mockTemplate]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Failed to load templates/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Full Body 3x/Week')).toBeInTheDocument();
    });
  });

  it('should show empty state when no templates', async () => {
    vi.mocked(templatesApi.listTemplates).mockResolvedValue([]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No templates found/i)).toBeInTheDocument();
    });
  });
});
