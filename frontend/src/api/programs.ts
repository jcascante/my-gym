import { apiClient } from '@/api/client';
import type { ProgramCreationPayload } from '@/types/programCreation';

export async function createProgram(payload: ProgramCreationPayload): Promise<void> {
  await apiClient.post('/programs', payload);
}
