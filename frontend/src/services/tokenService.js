/**
 * TurSathi AI — Token & Session Management Service
 * 
 * Securely manages JWT access tokens and user profile cache in browser localStorage.
 * Includes in-memory fallback for environments where localStorage is disabled or restricted.
 */

const TOKEN_KEY = 'tursathi_access_token';
const USER_KEY = 'tursathi_user_profile';

// In-memory fallback
let memoryStorage = {};

function getStorage() {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      // Test read/write permissions
      const testKey = '__storage_test__';
      window.localStorage.setItem(testKey, testKey);
      window.localStorage.removeItem(testKey);
      return window.localStorage;
    } catch {
      return null;
    }
  }
  return null;
}

export function getAccessToken() {
  const storage = getStorage();
  if (storage) {
    return storage.getItem(TOKEN_KEY);
  }
  return memoryStorage[TOKEN_KEY] || null;
}

export function setAccessToken(token) {
  if (!token) return;
  const storage = getStorage();
  if (storage) {
    storage.setItem(TOKEN_KEY, token);
  } else {
    memoryStorage[TOKEN_KEY] = token;
  }
}

export function getUser() {
  const storage = getStorage();
  const raw = storage ? storage.getItem(USER_KEY) : memoryStorage[USER_KEY];
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setUser(user) {
  if (!user) return;
  const serialized = JSON.stringify(user);
  const storage = getStorage();
  if (storage) {
    storage.setItem(USER_KEY, serialized);
  } else {
    memoryStorage[USER_KEY] = serialized;
  }
}

export function setAuth(token, user) {
  setAccessToken(token);
  if (user) {
    setUser(user);
  }
}

export function clearAuth() {
  const storage = getStorage();
  if (storage) {
    storage.removeItem(TOKEN_KEY);
    storage.removeItem(USER_KEY);
  }
  memoryStorage = {};
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

export const tokenService = {
  getAccessToken,
  setAccessToken,
  getUser,
  setUser,
  setAuth,
  clearAuth,
  isAuthenticated,
  getToken: getAccessToken,
  setToken: (token, user) => setAuth(token, user),
  clear: clearAuth,
};

export default tokenService;
