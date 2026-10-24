import test from 'node:test';
import assert from 'node:assert/strict';
import { tokenService } from '../src/services/tokenService.js';
import { authService } from '../src/services/authService.js';

test('Authentication Guard: detects unauthenticated session for route protection', () => {
  tokenService.clear();
  assert.equal(tokenService.isAuthenticated(), false);
  assert.equal(tokenService.getUser(), null);
});

test('Authentication Guard: recognizes authenticated session and preserves farmer credentials', () => {
  tokenService.clear();
  const mockUser = {
    id: 301,
    full_name: 'Anand Shinde',
    mobile_number: '9822012345',
    email: 'anand@farm.in',
  };

  tokenService.setToken('session-jwt-token-999', mockUser);
  assert.equal(tokenService.isAuthenticated(), true);
  assert.equal(tokenService.getToken(), 'session-jwt-token-999');
  assert.equal(tokenService.getUser().full_name, 'Anand Shinde');

  tokenService.clear();
  assert.equal(tokenService.isAuthenticated(), false);
});
