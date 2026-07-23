import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReadinessModal } from '@/components/ReadinessModal';

describe('ReadinessModal', () => {
  const mockOnRate = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnRate.mockClear();
    mockOnClose.mockClear();
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={false}
        onClose={mockOnClose}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders modal when isOpen is true', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    expect(screen.getByText('How are you feeling?')).toBeInTheDocument();
  });

  it('renders 1-5 rating buttons', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByRole('button', { name: String(i) })).toBeInTheDocument();
    }
  });

  it('highlights selected rating button', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button4 = screen.getByRole('button', { name: '4' });
    fireEvent.click(button4);
    expect(button4).toHaveClass('border-primary-600', 'bg-primary-100');
  });

  it('renders Skip and Submit buttons', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('calls onRate with selected readiness on submit', async () => {
    mockOnRate.mockResolvedValue(undefined);
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button3 = screen.getByRole('button', { name: '3' });
    const submitBtn = screen.getByRole('button', { name: /submit/i });

    fireEvent.click(button3);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockOnRate).toHaveBeenCalledWith(3);
    });
  });

  it('closes modal after successful submit', async () => {
    mockOnRate.mockResolvedValue(undefined);
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button2 = screen.getByRole('button', { name: '2' });
    const submitBtn = screen.getByRole('button', { name: /submit/i });

    fireEvent.click(button2);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('calls onClose when Skip is clicked', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const skipBtn = screen.getByRole('button', { name: /skip/i });
    fireEvent.click(skipBtn);
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('does not call onRate when Skip is clicked', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button5 = screen.getByRole('button', { name: '5' });
    const skipBtn = screen.getByRole('button', { name: /skip/i });

    fireEvent.click(button5);
    fireEvent.click(skipBtn);
    expect(mockOnRate).not.toHaveBeenCalled();
  });

  it('disables buttons during loading', async () => {
    mockOnRate.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button1 = screen.getByRole('button', { name: '1' });
    const submitBtn = screen.getByRole('button', { name: /submit/i });

    fireEvent.click(button1);
    fireEvent.click(submitBtn);

    expect(submitBtn).toBeDisabled();
    expect(screen.getByRole('button', { name: /skip/i })).toBeDisabled();

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('disables submit button when no rating selected', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const submitBtn = screen.getByRole('button', { name: /submit/i });
    expect(submitBtn).toBeDisabled();
  });

  it('enables submit button when rating is selected', () => {
    render(
      <ReadinessModal
        title="How are you feeling?"
        onRate={mockOnRate}
        isOpen={true}
        onClose={mockOnClose}
      />,
    );
    const button4 = screen.getByRole('button', { name: '4' });
    const submitBtn = screen.getByRole('button', { name: /submit/i });

    fireEvent.click(button4);
    expect(submitBtn).not.toBeDisabled();
  });
});
