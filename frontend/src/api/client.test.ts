import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, getSystemInfo } from './client';

afterEach(() => vi.unstubAllGlobals());

test('sends cookie credentials and cancellation signal to the same-origin API', async () => {
  const info = { name: 'CastraVolt', stage: 'foundation', capabilities: { accounts: false } };
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(info)));
  vi.stubGlobal('fetch', fetcher);
  const signal = new AbortController().signal;
  expect(await getSystemInfo(signal)).toEqual(info);
  expect(fetcher).toHaveBeenCalledWith('/api/v1/system', { credentials: 'include', signal });
});

test('preserves request reference on errors without crashing on non-JSON responses', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Unavailable', {
    status: 503, headers: { 'X-Request-ID': 'reference-1' },
  })));
  try { await getSystemInfo(); throw new Error('Expected rejection'); }
  catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 503, requestId: 'reference-1' });
  }
});
