/**
 * TurSathi AI — Frontend API Client Configuration
 * 
 * Provides unified HTTP client with:
 * - Dynamic base URL from VITE_API_BASE_URL (defaults to http://localhost:8000/api/v1)
 * - Automatic Bearer token attachment from tokenService
 * - FastAPI 422 validation error unpacking
 * - Timeout handling via AbortController
 * - Unified ApiError classification
 */

import { getAccessToken } from '../services/tokenService.js';

// Base URL configuration (Vite environment variable with local fallback)
export const API_BASE_URL = (
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://localhost:8000/api/v1'
).replace(/\/+$/, '');

/**
 * Custom API Error carrying HTTP status, detailed error messages, and network failure flags.
 */
export class ApiError extends Error {
  constructor(status, detail, { isNetworkError = false, isTimeout = false } = {}) {
    super(typeof detail === 'string' ? detail : 'An unexpected API error occurred.');
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.isNetworkError = isNetworkError;
    this.isTimeout = isTimeout;
  }
}

/**
 * Formats FastAPI error responses into human-friendly strings.
 * Handles:
 * 1. Simple string details: {"detail": "Invalid credentials"}
 * 2. Validation error arrays: {"detail": [{"loc": ["body", "mobile_number"], "msg": "..."}]}
 * 3. Malformed/missing error objects.
 *
 * @param {any} data - Parsed JSON response from server
 * @param {string} fallback - Default message if detail cannot be extracted
 * @returns {string} Formatted error string
 */
export function extractErrorDetail(data, fallback = 'Unable to complete request. Please try again.') {
  if (!data) return fallback;

  // Case 1: Simple string
  if (typeof data.detail === 'string' && data.detail.trim()) {
    return data.detail.trim();
  }

  // Case 2: Array of Pydantic validation errors
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const messages = data.detail.map((err) => {
      if (typeof err === 'string') return err;
      if (err && typeof err === 'object') {
        const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : null;
        const msg = err.msg || 'Invalid value';
        if (field && field !== 'body') {
          // Humanize field name (e.g. mobile_number -> Mobile Number)
          const humanField = field
            .split('_')
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');
          return `${humanField}: ${msg}`;
        }
        return msg;
      }
      return fallback;
    });
    return messages.join('. ');
  }

  // Case 3: Detail is an object with message
  if (data.detail && typeof data.detail === 'object') {
    if (typeof data.detail.message === 'string' && data.detail.message.trim()) {
      return data.detail.message.trim();
    }
  }

  // Case 4: Top-level message or error field
  if (typeof data.message === 'string' && data.message.trim()) {
    return data.message.trim();
  }
  if (typeof data.error === 'string' && data.error.trim()) {
    return data.error.trim();
  }

  return fallback;
}

/**
 * Robust fetch wrapper with timeout, token injection, and error formatting.
 *
 * @param {string} endpoint - Path relative to API_BASE_URL (e.g. "/auth/login") or full URL
 * @param {RequestInit & { timeout?: number, requiresAuth?: boolean }} options
 * @returns {Promise<any>}
 */
export async function apiFetch(endpoint, options = {}) {
  const {
    timeout = 15000,
    requiresAuth = true,
    headers = {},
    body,
    ...customConfig
  } = options;

  const url = endpoint.startsWith('http://') || endpoint.startsWith('https://')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Assemble headers
  const requestHeaders = new Headers(headers);

  // Attach auth token if available and required
  if (requiresAuth && !requestHeaders.has('Authorization')) {
    const token = getAccessToken();
    if (token) {
      requestHeaders.set('Authorization', `Bearer ${token}`);
    }
  }

  // Handle JSON content-type (do not set for FormData / multipart)
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  if (!isFormData && !requestHeaders.has('Content-Type') && body) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...customConfig,
      headers: requestHeaders,
      body: isFormData ? body : (typeof body === 'object' && body !== null ? JSON.stringify(body) : body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Parse JSON or text response
    let responseData = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        responseData = await response.json();
      } catch {
        responseData = null;
      }
    } else {
      try {
        const text = await response.text();
        responseData = text ? { detail: text } : null;
      } catch {
        responseData = null;
      }
    }

    if (!response.ok) {
      const errorMsg = extractErrorDetail(
        responseData,
        `Server returned error ${response.status} (${response.statusText || 'Error'}).`
      );
      throw new ApiError(response.status, errorMsg, { isNetworkError: false, isTimeout: false });
    }

    return responseData;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error.name === 'AbortError') {
      throw new ApiError(
        0,
        'Connection timed out. Please check your internet connection and try again.',
        { isNetworkError: true, isTimeout: true }
      );
    }

    throw new ApiError(
      0,
      'Unable to connect to the TurSathi server. Please ensure the backend is running.',
      { isNetworkError: true, isTimeout: false }
    );
  }
}
