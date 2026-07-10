import axios, { AxiosError } from 'axios';
import { useAuthStore } from '@/store/auth';
import type { UserProfile } from '@/store/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  // Tokens live in httpOnly cookies set by the backend; the browser attaches
  // them automatically as long as credentials are included on every request.
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }
    return Promise.reject(error);
  },
);

export interface SignupPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserWithProfileResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  profile?: UserProfile | null;
}

export async function signup(payload: SignupPayload): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>('/auth/signup', payload);
  return response.data;
}

export async function login(payload: LoginPayload): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>('/auth/login', payload);
  return response.data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout');
}

export async function refreshToken(): Promise<void> {
  await apiClient.post('/auth/refresh');
}

export async function getCurrentUser(): Promise<UserWithProfileResponse> {
  const response = await apiClient.get<UserWithProfileResponse>('/users/me');
  return response.data;
}

export async function saveUserProfile(profile: UserProfile): Promise<UserWithProfileResponse> {
  const response = await apiClient.post<UserWithProfileResponse>('/users/profile', profile);
  return response.data;
}
