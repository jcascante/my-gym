import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import * as authApi from '@/api/auth'
import { useAuthStore } from '@/store/auth'

vi.mock('@/api/auth')
vi.mock('@/store/auth')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should render login form', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      setAuth: vi.fn(),
    } as any)

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument()
  })

  it('should login successfully without profile', async () => {
    const setAuthMock = vi.fn()
    vi.mocked(useAuthStore).mockReturnValue({
      setAuth: setAuthMock,
    } as any)

    const mockUserData = {
      id: 1,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: null,
    }

    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'test_token',
      refresh_token: 'refresh_token',
      token_type: 'bearer',
    })

    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUserData)
    vi.mocked(authApi.setAuthToken).mockImplementation(() => {})

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
      expect(authApi.getCurrentUser).toHaveBeenCalled()
      expect(setAuthMock).toHaveBeenCalledWith(
        mockUserData,
        'test_token',
        'refresh_token',
        null
      )
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('should login successfully with profile', async () => {
    const setAuthMock = vi.fn()
    vi.mocked(useAuthStore).mockReturnValue({
      setAuth: setAuthMock,
    } as any)

    const mockUserData = {
      id: 1,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
      profile: {
        id: 1,
        age: 30,
        gender: 'male',
        weight_kg: 75.5,
      },
    }

    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'test_token',
      refresh_token: 'refresh_token',
      token_type: 'bearer',
    })

    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUserData)
    vi.mocked(authApi.setAuthToken).mockImplementation(() => {})

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(setAuthMock).toHaveBeenCalledWith(
        mockUserData,
        'test_token',
        'refresh_token',
        mockUserData.profile
      )
    })
  })

  it('should display error on login failure', async () => {
    const setAuthMock = vi.fn()
    vi.mocked(useAuthStore).mockReturnValue({
      setAuth: setAuthMock,
    } as any)

    const errorMessage = 'Invalid credentials'
    vi.mocked(authApi.login).mockRejectedValue(new Error(errorMessage))

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrongpassword' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })
})
