import type { Template } from '@/types/template';
import { apiClient } from '@/api/client';
import { getErrorMessage } from '@/api/errors';

export async function listTemplates(): Promise<Template[]> {
  try {
    const response = await apiClient.get<{ templates: Template[] }>('/templates');
    return response.data.templates;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
