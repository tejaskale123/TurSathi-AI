/**
 * TurSathi AI — Scan & Prediction Service
 * 
 * Interacts with FastAPI scan and diagnostic endpoints:
 * - POST /api/v1/scans (Upload image and create scan)
 * - GET  /api/v1/scans/{scan_id} (Retrieve scan details)
 * - POST /api/v1/scans/validate-frame (Stateless camera frame validation)
 * - POST /api/v1/predictions/tur-leaf/{scan_id} (Run ML leaf disease prediction)
 * - POST /api/v1/predictions/tur-leaf/{scan_id}/ai-guidance (Claude Sonnet 4.5 AI guidance)
 */

import { apiFetch } from '../config/api.js';

const RECENT_SCANS_KEY = 'tursathi_recent_scans';
let memoryRecentScans = [];

function getStorage() {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const testKey = '__storage_test__';
      window.localStorage.setItem(testKey, testKey);
      window.localStorage.removeItem(testKey);
      return window.localStorage;
    } catch {
      return null;
    }
  }
  if (typeof globalThis !== 'undefined' && globalThis.localStorage) {
    try {
      const testKey = '__storage_test__';
      globalThis.localStorage.setItem(testKey, testKey);
      globalThis.localStorage.removeItem(testKey);
      return globalThis.localStorage;
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Returns locally tracked recent scans from the current user session.
 * @returns {Array<any>}
 */
export function getRecentScans() {
  const storage = getStorage();
  if (storage) {
    try {
      const raw = storage.getItem(RECENT_SCANS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return memoryRecentScans;
    }
  }
  return memoryRecentScans;
}

/**
 * Saves a completed or updated scan to local session storage.
 * @param {any} scan
 */
export function recordRecentScan(scan) {
  if (!scan || !scan.scan_id) return;
  const current = getRecentScans();
  const filtered = current.filter((s) => s.scan_id !== scan.scan_id);
  const updated = [
    {
      ...scan,
      updated_at: scan.updated_at || new Date().toISOString(),
    },
    ...filtered,
  ].slice(0, 30); // Keep last 30 scans

  const storage = getStorage();
  if (storage) {
    try {
      storage.setItem(RECENT_SCANS_KEY, JSON.stringify(updated));
    } catch {
      // Ignore storage errors
    }
  }
  memoryRecentScans = updated;
}

/**
 * Uploads a Tur leaf image for disease diagnosis.
 *
 * @param {File | Blob} file
 * @param {string} [filename]
 * @returns {Promise<{
 *   scan_id: number,
 *   crop: string,
 *   status: string
 * }>}
 */
export async function uploadScan(file, filename = 'leaf_scan.jpg') {
  const formData = new FormData();
  formData.append('image', file, filename);
  formData.append('crop', 'tur');

  const data = await apiFetch('/scans', {
    method: 'POST',
    requiresAuth: true,
    body: formData,
    timeout: 30000,
  });

  if (data?.scan_id) {
    recordRecentScan({
      scan_id: data.scan_id,
      crop: data.crop || 'tur',
      status: data.status || 'received',
      created_at: new Date().toISOString(),
    });
  }

  return data;
}

/**
 * Runs ML disease prediction on a stored scan.
 * Calls FastAPI POST /predictions/tur-leaf/{scan_id}
 *
 * @param {number} scanId
 * @returns {Promise<{
 *   scan_id: number,
 *   crop: string,
 *   status: string,
 *   disease_name: string,
 *   confidence: number,
 *   severity: string
 * }>}
 */
export async function runPrediction(scanId) {
  try {
    const result = await apiFetch(`/predictions/tur-leaf/${scanId}`, {
      method: 'POST',
      requiresAuth: true,
      timeout: 30000,
    });

    recordRecentScan({
      scan_id: result.scan_id || scanId,
      crop: result.crop || 'tur',
      disease_name: result.disease_name,
      confidence: result.confidence,
      severity: result.severity,
      status: result.status || 'completed',
      created_at: new Date().toISOString(),
    });

    return result;
  } catch (err) {
    // Check fallback endpoint if exists
    if (err.status === 404) {
      const fallback = await apiFetch(`/scans/${scanId}/predict`, {
        method: 'POST',
        requiresAuth: true,
        timeout: 30000,
      });
      return fallback;
    }
    throw err;
  }
}

/**
 * Retrieves secondary AI guidance and explanation layer powered by Claude.
 * Calls POST /predictions/tur-leaf/{scan_id}/ai-guidance?language={lang}
 *
 * @param {number} scanId
 * @param {string} [language="en"] - "en" | "mr" | "hi"
 * @returns {Promise<any>}
 */
export async function getAiGuidance(scanId, language = 'en') {
  return apiFetch(`/predictions/tur-leaf/${scanId}/ai-guidance?language=${encodeURIComponent(language)}`, {
    method: 'POST',
    requiresAuth: true,
    timeout: 35000,
  });
}

/**
 * Statelessly validates a camera snapshot frame without creating database records.
 * Calls POST /scans/validate-frame
 *
 * @param {File | Blob} file
 * @returns {Promise<{
 *   is_valid_tur: boolean,
 *   label: string,
 *   confidence: number,
 *   reason?: string,
 *   message?: string,
 *   message_mr?: string
 * }>}
 */
export async function validateFrame(file) {
  const formData = new FormData();
  formData.append('image', file, 'frame_probe.jpg');

  return apiFetch('/scans/validate-frame', {
    method: 'POST',
    requiresAuth: true,
    body: formData,
    timeout: 15000,
  });
}

/**
 * Retrieves detailed scan information including predictions and status.
 * Calls GET /scans/{scan_id}
 *
 * @param {number} scanId
 * @returns {Promise<any>}
 */
export async function getScanDetail(scanId) {
  const detail = await apiFetch(`/scans/${scanId}`, {
    method: 'GET',
    requiresAuth: true,
  });

  if (detail?.scan_id) {
    recordRecentScan(detail);
  }

  return detail;
}

/**
 * Retrieves scan history for the authenticated farmer.
 * If backend list endpoint is available, fetches from API.
 * Otherwise provides tracked scans from current farmer session.
 *
 * @param {number|object} [skipOrOptions=0]
 * @param {number} [limitParam=50]
 * @returns {Promise<{ items: Array<any>, total: number }>}
 */
export async function getScanHistory(skipOrOptions = 0, limitParam = 20) {
  let skip = 0;
  let limit = 20;
  let page = null;

  if (typeof skipOrOptions === 'object' && skipOrOptions !== null) {
    skip = skipOrOptions.skip ?? 0;
    limit = skipOrOptions.limit ?? 20;
    page = skipOrOptions.page ?? null;
  } else {
    skip = skipOrOptions ?? 0;
    limit = limitParam ?? 20;
  }

  const queryParams = new URLSearchParams();
  if (page !== null) {
    queryParams.set('page', page);
  } else {
    queryParams.set('skip', skip);
  }
  queryParams.set('limit', limit);

  const data = await apiFetch(`/scans/?${queryParams.toString()}`, {
    method: 'GET',
    requiresAuth: true,
  });

  if (data && Array.isArray(data.items)) {
    return data;
  }
  if (Array.isArray(data)) {
    return { items: data, total: data.length, page: 1, limit };
  }
  return { items: [], total: 0, page: 1, limit };
}

export const scanService = {
  uploadScan,
  runPrediction,
  getAiGuidance,
  validateFrame,
  getScanDetail,
  getScanHistory,
  getRecentScans,
  recordRecentScan,
};

export default scanService;
