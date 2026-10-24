import test from 'node:test';
import assert from 'node:assert/strict';
import {
  API_BASE_URL,
  ApiError,
  extractErrorDetail,
  apiFetch,
} from '../src/config/api.js';

test('API Configuration: defaults to http://localhost:8000/api/v1', () => {
  assert.ok(API_BASE_URL);
  assert.match(API_BASE_URL, /localhost:8000\/api\/v1/);
});

test('extractErrorDetail: handles string error detail', () => {
  const detail = extractErrorDetail({ detail: 'Invalid mobile or password' });
  assert.equal(detail, 'Invalid mobile or password');
});

test('extractErrorDetail: formats FastAPI/Pydantic 422 validation array', () => {
  const pydanticError = {
    detail: [
      {
        loc: ['body', 'password'],
        msg: 'String should have at least 8 characters',
        type: 'string_too_short',
      },
      {
        loc: ['body', 'mobile_number'],
        msg: 'Mobile number must be a valid 10-digit Indian number',
        type: 'value_error',
      },
    ],
  };

  const formatted = extractErrorDetail(pydanticError);
  assert.match(formatted, /password: String should have at least 8 characters/i);
  assert.match(formatted, /mobile number: Mobile number must be a valid 10-digit Indian number/i);
});

test('extractErrorDetail: handles empty or missing payload with fallback', () => {
  assert.equal(extractErrorDetail(null, 'Custom fallback'), 'Custom fallback');
  assert.equal(extractErrorDetail({}, 'Custom fallback'), 'Custom fallback');
});

test('ApiError: constructs accurate error attributes', () => {
  const err = new ApiError(401, 'Invalid credentials');
  assert.equal(err.status, 401);
  assert.equal(err.detail, 'Invalid credentials');
  assert.equal(err.isNetworkError, false);
  assert.equal(err.isTimeout, false);
});

test('apiFetch: successfully performs GET request and parses JSON', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/test-endpoint$/);
      return {
        ok: true,
        status: 200,
        headers: {
          get: (name) => (name.toLowerCase() === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({ status: 'ok', data: 42 }),
      };
    };

    const response = await apiFetch('/test-endpoint');
    assert.deepEqual(response, { status: 'ok', data: 42 });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('apiFetch: throws ApiError on 422 validation error', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: false,
      status: 422,
      headers: {
        get: () => 'application/json',
      },
      json: async () => ({
        detail: [{ loc: ['body', 'password'], msg: 'Too short' }],
      }),
    });

    await assert.rejects(
      async () => {
        await apiFetch('/auth/register', { method: 'POST', body: {} });
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 422);
        assert.match(err.detail, /password: Too short/i);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('apiFetch: handles network failure gracefully', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      throw new TypeError('Failed to fetch');
    };

    await assert.rejects(
      async () => {
        await apiFetch('/health');
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.isNetworkError, true);
        assert.match(err.detail, /Unable to connect to the TurSathi server/i);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('apiFetch: attaches Bearer token when requiresAuth is true', async () => {
  const originalFetch = globalThis.fetch;
  const { setAccessToken, clearAuth } = await import('../src/services/tokenService.js');
  setAccessToken('mock-secret-token');

  try {
    let capturedHeaders = null;
    globalThis.fetch = async (url, options) => {
      capturedHeaders = options.headers;
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({ authenticated: true }),
      };
    };

    const res = await apiFetch('/protected', { requiresAuth: true });
    assert.equal(capturedHeaders.get('Authorization'), 'Bearer mock-secret-token');
    assert.deepEqual(res, { authenticated: true });
  } finally {
    globalThis.fetch = originalFetch;
    clearAuth();
  }
});

test('apiFetch: handles FormData without overriding multipart boundary header', async () => {
  const originalFetch = globalThis.fetch;
  try {
    let capturedHeaders = null;
    globalThis.fetch = async (url, options) => {
      capturedHeaders = options.headers;
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({ uploaded: true }),
      };
    };

    const formData = new FormData();
    formData.append('key', 'value');

    await apiFetch('/upload', { method: 'POST', body: formData });
    assert.equal(capturedHeaders.get('Content-Type'), null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('apiFetch: flags timeout errors when request aborts', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      const abortError = new Error('The operation was aborted');
      abortError.name = 'AbortError';
      throw abortError;
    };

    await assert.rejects(
      async () => {
        await apiFetch('/slow-endpoint', { timeout: 10 });
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.isTimeout, true);
        assert.match(err.detail, /timed out/i);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
