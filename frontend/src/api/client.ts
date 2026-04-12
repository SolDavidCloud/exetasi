import createClient from 'openapi-fetch';

import type { paths } from 'src/api/generated/paths';

let client: ReturnType<typeof createClient<paths>> | undefined;

export function getApiBaseUrl(): string {
  const url = import.meta.env.EXETASI_API_BASE_URL;
  if (typeof url === 'string' && url.length > 0) {
    return url.replace(/\/$/, '');
  }
  // In dev, Quasar proxies `/api` to the FastAPI backend so cookies stay first-party on the SPA origin.
  if (import.meta.env.DEV) {
    return '';
  }
  throw new Error('EXETASI_API_BASE_URL is not configured');
}

export function createApiClient(): ReturnType<typeof createClient<paths>> {
  const baseUrl = getApiBaseUrl();
  return createClient<paths>({ baseUrl, credentials: 'include' });
}

export function initApiClient(): ReturnType<typeof createClient<paths>> {
  client = createApiClient();
  return client;
}

export function getApiClient(): ReturnType<typeof createClient<paths>> {
  if (!client) {
    throw new Error('API client not initialized (boot/api missing?)');
  }
  return client;
}
