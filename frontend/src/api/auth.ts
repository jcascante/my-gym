import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
})

export interface SignupPayload {
  email: string
  password: string
  first_name: string
  last_name: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserResponse {
  id: number
  email: string
  first_name: string
  last_name: string
}

export async function signup(payload: SignupPayload): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>('/auth/signup', payload)
  return response.data
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', payload)
  return response.data
}

export async function logout(): Promise<void> {
  const token = localStorage.getItem('authToken')
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }
  await apiClient.post('/auth/logout')
  delete apiClient.defaults.headers.common['Authorization']
}

export async function refreshToken(refreshToken: string): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return response.data
}

export function setAuthToken(token: string): void {
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`
  localStorage.setItem('authToken', token)
}

export function clearAuthToken(): void {
  delete apiClient.defaults.headers.common['Authorization']
  localStorage.removeItem('authToken')
}
