import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SignupPage from '@/pages/SignupPage';
import * as authApi from '@/api/auth';
import { useAuthStore } from '@/store/auth';

vi.mock('@/api/auth');
vi.mock('@/store/auth');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('SignupPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('should render signup form', () => {
    const setAuthMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({ setAuth: setAuthMock }),
    );

    render(
      <BrowserRouter>
        <SignupPage />
      </BrowserRouter>,
    );

    expect(screen.getByText('Create your account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('John')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Doe')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create account/i })).toBeInTheDocument();
  });

  it('should signup successfully with profile', async () => {
    const setAuthMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({ setAuth: setAuthMock }),
    );

    const mockUserData = {
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
      profile: {
        id: 1,
        age: 25,
        gender: 'female',
      },
    };

    vi.mocked(authApi.signup).mockResolvedValue({
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
    });

    vi.mocked(authApi.login).mockResolvedValue({
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
    });

    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUserData);

    render(
      <BrowserRouter>
        <SignupPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByPlaceholderText('John'), { target: { value: 'Jane' } });
    fireEvent.change(screen.getByPlaceholderText('Doe'), { target: { value: 'Smith' } });
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'newuser@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));

    await waitFor(() => {
      expect(authApi.signup).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        password: 'password123',
        first_name: 'Jane',
        last_name: 'Smith',
      });
      expect(authApi.login).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        password: 'password123',
      });
      expect(authApi.getCurrentUser).toHaveBeenCalled();
      expect(setAuthMock).toHaveBeenCalledWith(mockUserData, mockUserData.profile);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should signup successfully without profile', async () => {
    const setAuthMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({ setAuth: setAuthMock }),
    );

    const mockUserData = {
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
      profile: null,
    };

    vi.mocked(authApi.signup).mockResolvedValue({
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
    });

    vi.mocked(authApi.login).mockResolvedValue({
      id: 2,
      email: 'newuser@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
    });

    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUserData);

    render(
      <BrowserRouter>
        <SignupPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByPlaceholderText('John'), { target: { value: 'Jane' } });
    fireEvent.change(screen.getByPlaceholderText('Doe'), { target: { value: 'Smith' } });
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'newuser@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));

    await waitFor(() => {
      expect(setAuthMock).toHaveBeenCalledWith(mockUserData, null);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('should display error on signup failure', async () => {
    const setAuthMock = vi.fn();
    vi.mocked(useAuthStore).mockImplementation((selector: any) =>
      selector({ setAuth: setAuthMock }),
    );

    const errorMessage = 'Email already exists';
    vi.mocked(authApi.signup).mockRejectedValue(new Error(errorMessage));

    render(
      <BrowserRouter>
        <SignupPage />
      </BrowserRouter>,
    );

    fireEvent.change(screen.getByPlaceholderText('John'), { target: { value: 'Jane' } });
    fireEvent.change(screen.getByPlaceholderText('Doe'), { target: { value: 'Smith' } });
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'existing@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
