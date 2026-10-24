/**
 * TurSathi AI — Authentication Service
 * 
 * Interacts with FastAPI authentication endpoints:
 * - POST /api/v1/auth/register
 * - POST /api/v1/auth/login
 * - GET  /api/v1/auth/me
 */

import { apiFetch } from '../config/api.js';
import {
  setAccessToken,
  setUser,
  getUser,
  getAccessToken,
  clearAuth,
  isAuthenticated,
} from './tokenService.js';

/**
 * Strips formatting characters from mobile number and removes +91/91 prefix if 12 digits.
 * @param {string} raw
 * @returns {string}
 */
export function normalizeMobileNumber(raw) {
  if (!raw) return '';
  const cleaned = raw.replace(/[\s()\-\+]/g, '');
  if (cleaned.startsWith('91') && cleaned.length === 12) {
    return cleaned.slice(2);
  }
  if (cleaned.startsWith('0') && cleaned.length === 11) {
    return cleaned.slice(1);
  }
  return cleaned;
}

/**
 * Authenticates a user with mobile number or email and password.
 *
 * @param {{ identifier: string, password: string }} credentials
 * @returns {Promise<{ access_token: string, token_type: string, user: any }>}
 */
export async function login({ identifier, password }) {
  const trimmedId = (identifier || '').trim();
  const cleanedId = normalizeMobileNumber(trimmedId);
  const finalIdentifier = /^[6-9]\d{9}$/.test(cleanedId) ? cleanedId : trimmedId;

  const data = await apiFetch('/auth/login', {
    method: 'POST',
    requiresAuth: false,
    body: {
      identifier: finalIdentifier,
      password: password || '',
    },
  });

  if (data?.access_token) {
    setAccessToken(data.access_token);
    if (data.user) {
      setUser(data.user);
    }
  }

  return data;
}

/**
 * Registers a new farmer user account.
 *
 * @param {{
 *   fullName: string,
 *   mobileNumber: string,
 *   email?: string | null,
 *   password: string,
 *   confirmPassword: string
 * }} registrationData
 * @returns {Promise<{ access_token: string, token_type: string, user: any }>}
 */
export async function register({
  fullName,
  mobileNumber,
  email,
  password,
  confirmPassword,
}) {
  const cleanedMobile = normalizeMobileNumber(mobileNumber);
  const trimmedEmail = (email || '').trim().toLowerCase() || null;

  const data = await apiFetch('/auth/register', {
    method: 'POST',
    requiresAuth: false,
    body: {
      full_name: (fullName || '').trim(),
      mobile_number: cleanedMobile,
      email: trimmedEmail,
      password: password || '',
      confirm_password: confirmPassword || '',
    },
  });

  if (data?.access_token) {
    setAccessToken(data.access_token);
    if (data.user) {
      setUser(data.user);
    }
  }

  return data;
}

/**
 * Retrieves the profile of the currently authenticated farmer.
 *
 * @returns {Promise<any>}
 */
export async function getMe() {
  const user = await apiFetch('/auth/me', {
    method: 'GET',
    requiresAuth: true,
  });

  if (user) {
    setUser(user);
  }
  return user;
}

/**
 * Clears stored JWT token and user session data.
 */
export function logout() {
  clearAuth();
}

export { getUser, getAccessToken, isAuthenticated };

export const authService = {
  login,
  register,
  getMe,
  logout,
  normalizeMobileNumber,
  getUser,
  getAccessToken,
  isAuthenticated,
};

export default authService;
