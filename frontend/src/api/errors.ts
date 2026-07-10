import { AxiosError } from 'axios';

export interface ErrorResponse {
  detail: string;
  error_code?: string;
  errors?: Array<{ loc: string[]; msg: string; type: string }>;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as ErrorResponse | undefined;
    if (data?.detail) {
      return data.detail;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred';
}
