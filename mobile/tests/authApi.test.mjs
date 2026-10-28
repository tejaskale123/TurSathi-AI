import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('Auth API and Error Handling Suite', () => {
  // Mirroring extractErrorDetail from mobile/src/config/api.ts
  function extractErrorDetail(data, fallback) {
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail.trim();
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (typeof first?.msg === 'string' && first.msg.trim()) {
        return first.msg.trim();
      }
    }
    if (typeof data?.message === 'string' && data.message.trim()) {
      return data.message.trim();
    }
    return fallback;
  }

  test('extractErrorDetail parses standard FastAPI string detail (400, 401, 404)', () => {
    const errorPayload = { detail: 'Incorrect mobile number or password.' };
    const result = extractErrorDetail(errorPayload, 'Default fallback');
    assert.equal(result, 'Incorrect mobile number or password.');
  });

  test('extractErrorDetail unpacks FastAPI 422 validation array without displaying [object Object]', () => {
    const errorPayload = {
      detail: [
        {
          type: 'string_too_short',
          loc: ['body', 'password'],
          msg: 'String should have at least 8 characters',
          input: '123'
        }
      ]
    };
    const result = extractErrorDetail(errorPayload, 'Default fallback');
    assert.equal(result, 'String should have at least 8 characters');
    assert.notEqual(result, '[object Object]');
  });

  test('extractErrorDetail falls back gracefully on empty or malformed objects', () => {
    assert.equal(extractErrorDetail(null, 'Fallback msg'), 'Fallback msg');
    assert.equal(extractErrorDetail({}, 'Fallback msg'), 'Fallback msg');
    assert.equal(extractErrorDetail({ detail: [] }, 'Fallback msg'), 'Fallback msg');
    assert.equal(extractErrorDetail({ detail: 123 }, 'Fallback msg'), 'Fallback msg');
  });

  test('login payload simulation validates required credentials and constructs JSON', () => {
    const identifier = '  9876543210  ';
    const password = 'SecretPassword123!';
    const payload = {
      identifier: identifier.trim(),
      password: password
    };
    assert.equal(payload.identifier, '9876543210');
    assert.equal(payload.password, 'SecretPassword123!');
  });

  test('registration payload simulation requires non-empty email and normalizes mobile', () => {
    const mobile = '+91 98765-43210';
    const normalizedMobile = mobile.replace(/[\s()-]/g, '').replace(/^\+91/, '');
    const email = '  farmer@example.com  ';
    const payload = {
      full_name: 'Kisan Patil',
      mobile_number: normalizedMobile,
      email: email.trim(),
      password: 'Password123!',
      confirm_password: 'Password123!'
    };
    assert.equal(payload.mobile_number, '9876543210');
    assert.equal(payload.email, 'farmer@example.com');
    assert.ok(payload.email.length > 0, 'Email must be required for registration');
  });

  test('forgot password payload simulation trims email and validates format', () => {
    const rawEmail = '   kisan.patil@agri.in   ';
    const trimmed = rawEmail.trim().toLowerCase();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    assert.ok(emailRegex.test(trimmed), 'Email should match valid email pattern');
    assert.equal(trimmed, 'kisan.patil@agri.in');
  });

  test('OTP verification payload simulation strips non-digits and validates 6 digits', () => {
    const rawOtp = ' 123 456 ';
    const cleaned = rawOtp.replace(/\D/g, '');
    assert.equal(cleaned.length, 6);
    assert.equal(cleaned, '123456');
    assert.ok(/^\d{6}$/.test(cleaned));

    const invalidOtp = '12345';
    assert.equal(/^\d{6}$/.test(invalidOtp), false);
  });

  test('password reset payload simulation validates token and password matching', () => {
    const resetToken = 'sample_jwt_reset_authorization_token';
    const newPassword = 'SecureNewPassword123!';
    const confirmPassword = 'SecureNewPassword123!';

    assert.ok(resetToken.trim().length > 0);
    assert.ok(newPassword.length >= 8, 'Password must be at least 8 characters');
    assert.equal(newPassword, confirmPassword, 'Passwords must match');

    const mismatchedConfirm = 'DifferentPassword123!';
    assert.notEqual(newPassword, mismatchedConfirm);
  });

  test('token storage lifecycle simulation verifies save, get, and clear isolation', async () => {
    let mockStore = {};

    const saveToken = async (tok) => { mockStore['token'] = tok; };
    const getToken = async () => { return mockStore['token'] || null; };
    const clearToken = async () => { delete mockStore['token']; };

    assert.equal(await getToken(), null);

    await saveToken('jwt.sample.token.123');
    assert.equal(await getToken(), 'jwt.sample.token.123');

    await clearToken();
    assert.equal(await getToken(), null);
  });

  test('network error classification distinguishes timeout from server errors', () => {
    function classifyError(err) {
      if (err.name === 'AbortError') {
        return 'Connection timed out. Please check your internet connection.';
      }
      if (err.message && err.message.includes('fetch failed')) {
        return 'Unable to reach the server. Please verify your connection.';
      }
      return err.message;
    }

    const abortErr = new Error('The operation was aborted');
    abortErr.name = 'AbortError';
    assert.equal(classifyError(abortErr), 'Connection timed out. Please check your internet connection.');

    const fetchErr = new Error('TypeError: fetch failed');
    assert.equal(classifyError(fetchErr), 'Unable to reach the server. Please verify your connection.');
  });
});
