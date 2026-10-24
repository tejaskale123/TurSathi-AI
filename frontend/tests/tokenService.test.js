import test from 'node:test';
import assert from 'node:assert/strict';
import { tokenService } from '../src/services/tokenService.js';

test('tokenService: stores, retrieves, and clears token and user profile', () => {
  tokenService.clear();
  assert.equal(tokenService.getToken(), null);
  assert.equal(tokenService.getUser(), null);
  assert.equal(tokenService.isAuthenticated(), false);

  const mockUser = {
    id: 101,
    full_name: 'Ramesh Patil',
    mobile_number: '9876543210',
    email: 'ramesh@example.com',
  };

  tokenService.setToken('jwt-access-token-xyz', mockUser);

  assert.equal(tokenService.getToken(), 'jwt-access-token-xyz');
  assert.deepEqual(tokenService.getUser(), mockUser);
  assert.equal(tokenService.isAuthenticated(), true);

  tokenService.clear();

  assert.equal(tokenService.getToken(), null);
  assert.equal(tokenService.getUser(), null);
  assert.equal(tokenService.isAuthenticated(), false);
});
