import type { Template } from '@/types/template';
import { getErrorMessage } from '@/api/errors';

interface TemplatesResponse {
  templates: Template[];
}

export async function listTemplates(): Promise<Template[]> {
  try {
    const response = await fetch('/api/v1/templates');
    if (!response.ok) {
      const message =
        response.status === 500 ? 'Server error loading templates' : 'Failed to load templates';
      throw new Error(message);
    }
    const data = (await response.json()) as TemplatesResponse;
    return data.templates;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
