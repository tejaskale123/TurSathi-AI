/**
 * Scan API Service — Tur Leaf Image Upload Pipeline
 *
 * Responsibilities:
 * - Upload Tur leaf image to POST /api/v1/scans (multipart/form-data)
 * - Upload farmer voice recording to POST /api/v1/scans/{scan_id}/voice
 * - Provide structured error handling for every HTTP status code
 * - Prevent duplicate uploads via upload guard state (managed by caller)
 * - Never expose internal filesystem paths
 *
 * Security:
 * - Bearer JWT is passed from the calling screen's stored token
 * - File bytes are read from the stable local URI before upload
 * - Tokens are never logged
 */

import * as FileSystem from 'expo-file-system/legacy';
import { Platform } from 'react-native';
import { getBaseUrl, getHeaders } from './api';

const UPLOAD_TIMEOUT_MS = 30000; // 30 seconds for image upload
const VOICE_UPLOAD_TIMEOUT_MS = 60000; // 60 seconds for audio upload

// ── Response types ────────────────────────────────────────────────────────────

export interface ScanCreateResponse {
  scan_id: number;
  crop: string;
  status: string;
}

export interface VoiceReportCreateResponse {
  voice_report_id: number;
  scan_id: number;
  language: string | null;
  status: string;
}

export interface PredictionResponse {
  scan_id: number;
  crop: string;
  status: string;
  message: string | null;
  disease_name: string | null;
  confidence: number | null;
  severity: string | null;
}

// ── Error classification ──────────────────────────────────────────────────────

export class ScanUploadError extends Error {
  constructor(
    public readonly httpStatus: number | null,
    message: string,
    public readonly isRetryable: boolean = true,
    public readonly reason?: string,
    public readonly messageMr?: string,
  ) {
    super(message);
    this.name = 'ScanUploadError';
  }
}

function classifyHttpError(status: number, rawDetail?: any): ScanUploadError {
  let msg = `Server error (HTTP ${status})`;
  let reason: string | undefined;
  let messageMr: string | undefined;

  if (typeof rawDetail === 'string') {
    msg = rawDetail;
  } else if (rawDetail && typeof rawDetail === 'object') {
    if (typeof rawDetail.message === 'string') msg = rawDetail.message;
    if (typeof rawDetail.reason === 'string') reason = rawDetail.reason;
    if (typeof rawDetail.message_mr === 'string') messageMr = rawDetail.message_mr;
  }

  switch (status) {
    case 400:
      return new ScanUploadError(400, msg || 'Bad request. Please try again.', false, reason, messageMr);
    case 401:
      return new ScanUploadError(
        401,
        (typeof rawDetail === 'string' && rawDetail.trim()) ||
        rawDetail?.message ||
        rawDetail?.detail ||
        'Session expired. Please log in again.',
        false,
        reason,
        messageMr,
      );
    case 403:
      return new ScanUploadError(403, 'Access denied.', false, reason, messageMr);
    case 404:
      return new ScanUploadError(404, 'Scan not found.', false, reason, messageMr);
    case 413:
      return new ScanUploadError(413, 'Image file is too large. Please use a smaller photo.', false, reason, messageMr);
    case 422:
      return new ScanUploadError(
        422,
        msg || 'Invalid image. Please capture a clear Tur leaf photo.',
        false,
        reason,
        messageMr,
      );
    case 429:
      return new ScanUploadError(429, 'Too many uploads. Please wait a moment and try again.', true, reason, messageMr);
    case 500:
      return new ScanUploadError(500, 'Server error. Please try again.', true, reason, messageMr);
    case 503:
      // model_not_configured is NOT an error for the upload pipeline — prediction is separate
      return new ScanUploadError(503, msg || 'Service temporarily unavailable.', true, reason, messageMr);
    default:
      return new ScanUploadError(status, msg, status >= 500, reason, messageMr);
  }
}


// ── Image upload ──────────────────────────────────────────────────────────────

/**
 * Uploads a Tur leaf image to the backend and creates a scan record.
 *
 * @param imageUri   Stable local file URI (from persistImageUri in scan.tsx)
 * @param token      Bearer JWT access token
 * @param crop       Crop type (default "tur")
 * @returns          ScanCreateResponse with scan_id
 * @throws           ScanUploadError with user-friendly message and retry hint
 */
export async function uploadScanImage(
  imageUri: string,
  token: string,
  crop: string = 'tur',
): Promise<ScanCreateResponse> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}/api/v1/scans`;
  console.log(`[SCAN API] Uploading image to: ${url}`);
  console.log(`[SCAN API] Attaching image URI: ${imageUri}`);

  // Native Mobile (Android / iOS): Use Expo FileSystem.uploadAsync for 100% reliable native multipart stream
  if (Platform.OS !== 'web') {
    try {
      const result = await FileSystem.uploadAsync(url, imageUri, {
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        fieldName: 'image',
        headers: getHeaders({
          Authorization: `Bearer ${token}`,
        }),
        parameters: {
          crop: crop,
        },
      });

      console.log(`[SCAN API] Native upload response status: ${result.status}, body: ${result.body}`);

      let data: any = {};
      try {
        data = JSON.parse(result.body);
      } catch {
        if (result.status < 200 || result.status >= 300) {
          throw new ScanUploadError(result.status, `Server returned HTTP ${result.status}.`, result.status >= 500);
        }
      }

      if (result.status < 200 || result.status >= 300) {
        throw classifyHttpError(result.status, data?.detail);
      }

      if (typeof data?.scan_id !== 'number') {
        throw new ScanUploadError(null, 'Invalid response from server. Please try again.', true);
      }

      return data as ScanCreateResponse;
    } catch (err: any) {
      if (err instanceof ScanUploadError) {
        throw err;
      }
      console.error('[SCAN API] Native uploadAsync error:', err);
      throw new ScanUploadError(
        null,
        'Unable to reach the server. Please check your connection.',
        true,
      );
    }
  }

  // Web fallback: fetch the blob: URL to get real image bytes, then POST with FormData
  const formData = new FormData();
  const filename = imageUri.split('/').pop() || 'tur_leaf.jpg';
  const ext = filename.split('.').pop()?.toLowerCase() || 'jpg';
  const mimeType =
    ext === 'png' ? 'image/png' :
    ext === 'webp' ? 'image/webp' :
    ext === 'heic' ? 'image/heic' :
    ext === 'heif' ? 'image/heif' :
    'image/jpeg';

  // Fetch the blob: URL to obtain the actual image bytes
  let blob: Blob;
  try {
    const blobResponse = await fetch(imageUri);
    if (!blobResponse.ok) {
      throw new ScanUploadError(null, 'Failed to read image data. Please try again.', true);
    }
    blob = await blobResponse.blob();
  } catch (err: any) {
    if (err instanceof ScanUploadError) throw err;
    throw new ScanUploadError(null, 'Failed to read image data. Please try again.', true);
  }

  // Use the blob's own MIME type if available, otherwise fall back to the detected mimeType
  const effectiveMime = blob.type || mimeType;
  const finalBlob = effectiveMime !== blob.type ? new Blob([blob], { type: effectiveMime }) : blob;

  formData.append('image', finalBlob, filename);

  formData.append('crop', crop);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: getHeaders({
        Authorization: `Bearer ${token}`,
      }),
      body: formData,
      signal: controller.signal,
    });
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new ScanUploadError(
        null,
        'Upload timed out. Please check your connection and try again.',
        true,
      );
    }
    throw new ScanUploadError(
      null,
      'Unable to reach the server. Please check your connection.',
      true,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  let data: any = {};
  try {
    data = await response.json();
  } catch {
    if (!response.ok) {
      throw new ScanUploadError(response.status, `Server returned HTTP ${response.status}.`, response.status >= 500);
    }
  }

  if (!response.ok) {
    throw classifyHttpError(response.status, data?.detail);
  }


  if (typeof data?.scan_id !== 'number') {
    throw new ScanUploadError(null, 'Invalid response from server. Please try again.', true);
  }

  return data as ScanCreateResponse;
}

// ── Voice upload ──────────────────────────────────────────────────────────────

/**
 * Uploads a farmer voice recording linked to the given scan.
 *
 * @param scanId     Scan ID returned by uploadScanImage
 * @param audioUri   Local file URI of the recorded audio
 * @param token      Bearer JWT access token
 * @param language   BCP-47 language code: "en" | "mr" | "hi"
 * @param duration   Recording duration in seconds (optional)
 * @returns          VoiceReportCreateResponse
 * @throws           ScanUploadError
 */
export async function uploadVoiceReport(
  scanId: number,
  audioUri: string,
  token: string,
  language?: string,
  duration?: number,
): Promise<VoiceReportCreateResponse> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}/api/v1/scans/${scanId}/voice`;
  console.log(`[SCAN API] Uploading voice report to: ${url}`);
  console.log(`[SCAN API] Attaching voice URI: ${audioUri}`);

  const parameters: Record<string, string> = {};
  if (language) parameters.language = language;
  if (duration !== undefined && duration !== null) parameters.duration = String(duration);

  // Native Mobile (Android / iOS)
  if (Platform.OS !== 'web') {
    try {
      const result = await FileSystem.uploadAsync(url, audioUri, {
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        fieldName: 'audio',
        headers: getHeaders({
          Authorization: `Bearer ${token}`,
        }),
        parameters,
      });

      console.log(`[SCAN API] Native voice upload response status: ${result.status}, body: ${result.body}`);

      let data: any = {};
      try {
        data = JSON.parse(result.body);
      } catch {
        if (result.status < 200 || result.status >= 300) {
          throw new ScanUploadError(result.status, `Server returned HTTP ${result.status}.`, result.status >= 500);
        }
      }

      if (result.status < 200 || result.status >= 300) {
        const detail = typeof data?.detail === 'string' ? data.detail : undefined;
        throw classifyHttpError(result.status, detail);
      }

      if (typeof data?.voice_report_id !== 'number') {
        throw new ScanUploadError(null, 'Invalid voice upload response from server.', true);
      }

      return data as VoiceReportCreateResponse;
    } catch (err: any) {
      if (err instanceof ScanUploadError) {
        throw err;
      }
      console.error('[SCAN API] Native voice uploadAsync error:', err);
      throw new ScanUploadError(
        null,
        'Unable to reach the server. Please check your connection.',
        true,
      );
    }
  }

  // Web fallback: fetch the blob: URL to get real audio bytes, then POST with FormData
  const formData = new FormData();
  const filename = audioUri.split('/').pop() || 'voice_report.m4a';
  const ext = filename.split('.').pop()?.toLowerCase() || 'm4a';
  const mimeType =
    ext === 'mp3' ? 'audio/mpeg' :
    ext === 'wav' ? 'audio/wav' :
    ext === 'webm' ? 'audio/webm' :
    ext === 'ogg' ? 'audio/ogg' :
    ext === 'aac' ? 'audio/aac' :
    ext === '3gp' ? 'audio/3gpp' :
    'audio/mp4';

  // Fetch the blob: URL to obtain the actual audio bytes
  let audioBlob: Blob;
  try {
    const audioResponse = await fetch(audioUri);
    if (!audioResponse.ok) {
      throw new ScanUploadError(null, 'Failed to read audio data. Please try again.', true);
    }
    audioBlob = await audioResponse.blob();
  } catch (err: any) {
    if (err instanceof ScanUploadError) throw err;
    throw new ScanUploadError(null, 'Failed to read audio data. Please try again.', true);
  }

  // Use the blob's own MIME type if available, otherwise fall back to the detected mimeType
  const effectiveAudioMime = audioBlob.type || mimeType;
  const finalAudioBlob = effectiveAudioMime !== audioBlob.type
    ? new Blob([audioBlob], { type: effectiveAudioMime })
    : audioBlob;

  formData.append('audio', finalAudioBlob, filename);

  if (language) formData.append('language', language);
  if (duration !== undefined && duration !== null) formData.append('duration', String(duration));

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), VOICE_UPLOAD_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: getHeaders({
        Authorization: `Bearer ${token}`,
      }),
      body: formData,
      signal: controller.signal,
    });
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new ScanUploadError(
        null,
        'Voice upload timed out. Please check your connection and try again.',
        true,
      );
    }
    throw new ScanUploadError(
      null,
      'Unable to reach the server. Please check your connection.',
      true,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  let data: any = {};
  try {
    data = await response.json();
  } catch {
    if (!response.ok) {
      throw new ScanUploadError(response.status, `Server returned HTTP ${response.status}.`, response.status >= 500);
    }
  }

  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : undefined;
    throw classifyHttpError(response.status, detail);
  }

  if (typeof data?.voice_report_id !== 'number') {
    throw new ScanUploadError(null, 'Invalid voice upload response from server.', true);
  }

  return data as VoiceReportCreateResponse;
}

// ── Prediction ────────────────────────────────────────────────────────────────

/**
 * Calls the ML prediction API for a specific scan.
 *
 * @param scanId     Scan ID returned by uploadScanImage
 * @param token      Bearer JWT access token
 * @returns          PredictionResponse
 * @throws           ScanUploadError
 */
export async function predictTurLeaf(
  scanId: number,
  token: string
): Promise<PredictionResponse> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}/api/v1/predictions/tur-leaf/${scanId}`;
  console.log(`[SCAN API] Requesting prediction for scan ${scanId} at: ${url}`);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: getHeaders({
        Authorization: `Bearer ${token}`,
      }),
    });

    let data: any = {};
    try {
      data = await response.json();
    } catch {
      if (!response.ok) {
        throw new ScanUploadError(response.status, `Server returned HTTP ${response.status}.`, response.status >= 500);
      }
    }

    if (!response.ok) {
      throw classifyHttpError(response.status, data?.detail);
    }


    return data as PredictionResponse;
  } catch (err: any) {
    if (err instanceof ScanUploadError) {
      throw err;
    }
    console.error('[SCAN API] predictTurLeaf error:', err);
    throw new ScanUploadError(
      null,
      'Unable to reach the server. Please check your connection.',
      true,
    );
  }
}

// ── Stateless Camera Frame Validation ─────────────────────────────────────────

export interface FrameValidationResponse {
  is_valid_tur: boolean;
  label: string;
  confidence: number;
  reason: string;
  message?: string | null;
}

/**
 * Statelessly validates a camera snapshot frame with the backend TurImageGate.
 * Does not create database records or store files on server disk.
 */
export async function validateCameraFrame(
  imageUri: string,
  token: string,
): Promise<FrameValidationResponse> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}/api/v1/scans/validate-frame`;

  if (Platform.OS !== 'web') {
    try {
      const result = await FileSystem.uploadAsync(url, imageUri, {
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        fieldName: 'image',
        headers: getHeaders({
          Authorization: `Bearer ${token}`,
        }),
      });

      if (result.status >= 200 && result.status < 300) {
        return JSON.parse(result.body) as FrameValidationResponse;
      }
      return {
        is_valid_tur: false,
        label: 'Error',
        confidence: 0,
        reason: `http_${result.status}`,
        message: 'Frame validation returned non-200 status',
      };
    } catch (err: any) {
      return {
        is_valid_tur: false,
        label: 'Error',
        confidence: 0,
        reason: 'network_error',
        message: err?.message || 'Network error during frame validation',
      };
    }
  } else {
    try {
      const blob = await (await fetch(imageUri)).blob();
      const formData = new FormData();
      formData.append('image', blob, 'probe_frame.jpg');

      const response = await fetch(url, {
        method: 'POST',
        headers: getHeaders({
          Authorization: `Bearer ${token}`,
        }),
        body: formData,
      });

      if (response.ok) {
        return (await response.json()) as FrameValidationResponse;
      }
      return {
        is_valid_tur: false,
        label: 'Error',
        confidence: 0,
        reason: `http_${response.status}`,
        message: 'Frame validation returned non-200 status',
      };
    } catch (err: any) {
      return {
        is_valid_tur: false,
        label: 'Error',
        confidence: 0,
        reason: 'network_error',
        message: err?.message || 'Network error during frame validation',
      };
    }
  }
}


