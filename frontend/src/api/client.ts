import type { components } from './schema';

export type SystemInfo = components['schemas']['SystemInfo'];

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly requestId?: string) {
    super(message);
  }
}

export async function getSystemInfo(signal?: AbortSignal): Promise<SystemInfo> {
  const response = await fetch('/api/v1/system', { credentials: 'include', signal });
  if (!response.ok) {
    if(response.status===401 && typeof window!=='undefined') window.dispatchEvent(new Event('castravolt:unauthenticated'));
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.error?.message ?? 'Unable to connect. Please try again.', response.status,
      response.headers.get('X-Request-ID') ?? undefined);
  }
  return response.json();
}
