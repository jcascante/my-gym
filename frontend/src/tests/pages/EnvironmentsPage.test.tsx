import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import EnvironmentsPage from '@/pages/EnvironmentsPage';
import * as trainingEnvironmentsApi from '@/api/trainingEnvironments';

vi.mock('@/api/trainingEnvironments');
vi.mock('@/api/programs');

const mockEnvironment = {
  id: 1,
  name: 'Home Gym',
  environment_type: 'home' as const,
  equipment_tags: ['dumbbells'],
  is_default: true,
};

function renderPage() {
  render(
    <BrowserRouter>
      <EnvironmentsPage />
    </BrowserRouter>,
  );
}

describe('EnvironmentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render an empty state when there are no environments', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/haven't added any training environments/i)).toBeInTheDocument();
    });
  });

  it('should render the list of environments', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([
      mockEnvironment,
    ]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Home Gym')).toBeInTheDocument();
    });
  });

  it('should add a new environment', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([mockEnvironment]);
    vi.mocked(trainingEnvironmentsApi.createTrainingEnvironment).mockResolvedValue(mockEnvironment);

    renderPage();

    await waitFor(() => screen.getByRole('button', { name: /Add Environment/i }));
    fireEvent.click(screen.getByRole('button', { name: /Add Environment/i }));

    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'Home Gym' } });
    fireEvent.click(screen.getByRole('button', { name: /Save Environment/i }));

    await waitFor(() => {
      expect(trainingEnvironmentsApi.createTrainingEnvironment).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Home Gym' }),
      );
      expect(screen.getByText('Home Gym')).toBeInTheDocument();
    });
  });

  it('should edit an existing environment', async () => {
    const updatedEnvironment = { ...mockEnvironment, name: 'Updated Gym' };
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments)
      .mockResolvedValueOnce([mockEnvironment])
      .mockResolvedValueOnce([updatedEnvironment]);
    vi.mocked(trainingEnvironmentsApi.updateTrainingEnvironment).mockResolvedValue(
      updatedEnvironment,
    );

    renderPage();

    await waitFor(() => screen.getByText('Home Gym'));
    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    const nameInput = screen.getByLabelText(/Name/);
    fireEvent.change(nameInput, { target: { value: 'Updated Gym' } });
    fireEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

    await waitFor(() => {
      expect(trainingEnvironmentsApi.updateTrainingEnvironment).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ name: 'Updated Gym' }),
      );
      expect(screen.getByText('Updated Gym')).toBeInTheDocument();
    });
  });

  it('should delete an environment after confirmation', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments)
      .mockResolvedValueOnce([mockEnvironment])
      .mockResolvedValueOnce([]);
    vi.mocked(trainingEnvironmentsApi.deleteTrainingEnvironment).mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    renderPage();

    await waitFor(() => screen.getByText('Home Gym'));
    fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

    await waitFor(() => {
      expect(trainingEnvironmentsApi.deleteTrainingEnvironment).toHaveBeenCalledWith(1);
      expect(screen.queryByText('Home Gym')).not.toBeInTheDocument();
    });
  });

  it('should not delete when confirmation is declined', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([
      mockEnvironment,
    ]);
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    renderPage();

    await waitFor(() => screen.getByText('Home Gym'));
    fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

    await waitFor(() => {
      expect(trainingEnvironmentsApi.deleteTrainingEnvironment).not.toHaveBeenCalled();
    });
  });

  it('should navigate to /programs/new when Generate Program is clicked', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockResolvedValue([
      mockEnvironment,
    ]);

    renderPage();

    await waitFor(() => screen.getByText('Home Gym'));
    const generateButton = screen.getByRole('link', { name: /Generate Program/i });

    expect(generateButton).toHaveAttribute('href', '/programs/new');
  });

  it('should display an error when loading environments fails', async () => {
    vi.mocked(trainingEnvironmentsApi.listTrainingEnvironments).mockRejectedValue(
      new Error('Network error'),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
