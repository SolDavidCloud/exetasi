import { describe, expect, it } from 'vitest';

import { getApiBaseUrl } from 'src/api/client';

describe('getApiBaseUrl', () => {
  it('returns a normalized base URL without trailing slash', () => {
    expect(getApiBaseUrl()).toBe('');
  });
});
