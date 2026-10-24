import test from 'node:test';
import assert from 'node:assert/strict';
import { authService } from '../src/services/authService.js';
import { tokenService } from '../src/services/tokenService.js';

test('authService.normalizeMobileNumber: strips prefixes, spaces, and punctuation', () => {
  assert.equal(authService.normalizeMobileNumber('+91 98765 43210'), '9876543210');
  assert.equal(authService.normalizeMobileNumber('09876543210'), '9876543210');
  assert.equal(authService.normalizeMobileNumber('98765-43210'), '9876543210');
  assert.equal(authService.normalizeMobileNumber('+919876543210'), '9876543210');
  assert.equal(authService.normalizeMobileNumber('  9876543210  '), '9876543210');
});

test('authService.login: stores token and profile on successful response', async () => {
  const originalFetch = globalThis.fetch;
  tokenService.clear();

  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/auth\/login$/);
      assert.equal(options.method, 'POST');
      const body = JSON.parse(options.body);
      assert.equal(body.identifier, '9876543210');
      assert.equal(body.password, 'Secret123');

      return {
        ok: true,
        status: 200,
        headers: {
          get: (name) => (name.toLowerCase() === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({
          access_token: 'auth-test-token-456',
          token_type: 'bearer',
          user: {
            id: 42,
            full_name: 'Test Farmer',
            mobile_number: '9876543210',
            email: null,
            is_active: true,
          },
        }),
      };
    };

    const result = await authService.login({
      identifier: '9876543210',
      password: 'Secret123',
    });

    assert.equal(result.access_token, 'auth-test-token-456');
    assert.equal(tokenService.getToken(), 'auth-test-token-456');
    assert.equal(tokenService.getUser().full_name, 'Test Farmer');
  } finally {
    globalThis.fetch = originalFetch;
    tokenService.clear();
  }
});

test('authService.register: properly structures registration payload', async () => {
  const originalFetch = globalThis.fetch;

  try {
    let capturedBody = null;
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/auth\/register$/);
      assert.equal(options.method, 'POST');
      capturedBody = JSON.parse(options.body);

      return {
        ok: true,
        status: 201,
        headers: {
          get: (name) => (name.toLowerCase() === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({
          id: 99,
          full_name: capturedBody.full_name,
          mobile_number: capturedBody.mobile_number,
          email: capturedBody.email,
          is_active: true,
          created_at: new Date().toISOString(),
        }),
      };
    };

    const res = await authService.register({
      fullName: 'Sunita Rao',
      mobileNumber: '+91 98765 11223',
      email: 'sunita@example.com',
      password: 'StrongPassword123',
      confirmPassword: 'StrongPassword123',
    });

    assert.equal(capturedBody.full_name, 'Sunita Rao');
    assert.equal(capturedBody.mobile_number, '9876511223');
    assert.equal(capturedBody.email, 'sunita@example.com');
    assert.equal(capturedBody.password, 'StrongPassword123');
    assert.equal(capturedBody.confirm_password, 'StrongPassword123');
    assert.equal(res.id, 99);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('authService.logout: clears saved credentials', () => {
  tokenService.setToken('temp-token', { name: 'Demo' });
  assert.ok(tokenService.isAuthenticated());

  authService.logout();

  assert.equal(tokenService.isAuthenticated(), false);
  assert.equal(tokenService.getToken(), null);
});

test('authService.login: rejects on invalid credentials with ApiError', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: false,
      status: 401,
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: 'Incorrect mobile number or password' }),
    });

    await assert.rejects(
      async () => {
        await authService.login({ identifier: '9876543210', password: 'wrong' });
      },
      (err) => {
        assert.equal(err.status, 401);
        assert.equal(err.detail, 'Incorrect mobile number or password');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
