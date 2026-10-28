import { getBaseUrl, getHeaders } from './api';

export interface SprayGuidanceResponse {
  crop: string;
  disease_name: string;
  leaf_condition: string;
  important_alert: string;
  spray_guidance: string[];
  after_spraying: string[];
  safety_precautions: string[];
  farmer_action: string;
}

export interface SprayGuidanceDetails {
  treatment: string | null;
  active_ingredient: string | null;
  recommended_quantity: string | null;
  water_quantity: string | null;
  per_pump_quantity: string | null;
  spray_timing: string | null;
  application_method: string | null;
  safety_precautions: string | null;
  after_spray_advisory: string | null;
}

export interface ClaudeGuidanceResponse {
  status: string;
  crop: string;
  disease_name: string | null;
  confidence: number | null;
  confidence_percent: number;
  disease_explanation: string;
  farmer_action: string[];
  spray_guidance_available: boolean;
  ai_guidance_available: boolean;
  spray_guidance: SprayGuidanceDetails | null;
  warnings: string[];
  language: string;
}

function extractErrorDetail(data: any, fallback: string): string {
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

export class RecommendationApiError extends Error {
  constructor(
    public readonly httpStatus: number | null,
    message: string,
    public readonly isNotFound: boolean = false,
  ) {
    super(message);
    this.name = 'RecommendationApiError';
    Object.setPrototypeOf(this, RecommendationApiError.prototype);
  }
}

export async function fetchTurSprayGuidance(
  diseaseName: string,
  token?: string,
): Promise<SprayGuidanceResponse> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}/api/v1/recommendations/tur/${encodeURIComponent(diseaseName)}/spray-guidance`;
  console.log(`[RECOMMENDATION API] Fetching spray guidance from: ${url}`);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: getHeaders(headers),
      signal: controller.signal,
    });

    if (response.status === 404) {
      const data = await response.json().catch(() => ({}));
      const message = extractErrorDetail(data, 'Verified spray guidance is not available for this condition yet.');
      throw new RecommendationApiError(404, message, true);
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const message = extractErrorDetail(data, `Server error (HTTP ${response.status})`);
      throw new RecommendationApiError(response.status, message, false);
    }

    const data = await response.json();
    return data as SprayGuidanceResponse;
  } catch (err: any) {
    if (err instanceof RecommendationApiError || err?.name === 'RecommendationApiError') {
      throw err;
    }
    if (err?.name === 'AbortError') {
      throw new RecommendationApiError(null, 'Connection timed out. Please try again.');
    }
    console.error('[RECOMMENDATION API] Tur spray guidance fetch error:', err);
    throw new RecommendationApiError(null, 'Unable to connect to server. Please check your connection.');
  } finally {
    clearTimeout(timeoutId);
  }
}

const AI_GUIDANCE_TIMEOUT_MS = 60000;

export async function fetchAIGuidance(
  scanId: number,
  language: string,
  token?: string,
  signal?: AbortSignal,
): Promise<ClaudeGuidanceResponse> {
  const baseUrl = getBaseUrl();
  const langQuery = language ? `?language=${encodeURIComponent(language)}` : '';
  const url = `${baseUrl}/api/v1/predictions/tur-leaf/${scanId}/ai-guidance${langQuery}`;
  console.log(`[RECOMMENDATION API] Fetching AI guidance from: ${url}`);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AI_GUIDANCE_TIMEOUT_MS);

  const onExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      clearTimeout(timeoutId);
      throw new RecommendationApiError(null, 'Request was canceled.');
    }
    signal.addEventListener('abort', onExternalAbort, { once: true });
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: getHeaders(headers),
      body: JSON.stringify({}),
      signal: controller.signal,
    });

    if (response.status === 404) {
      const data = await response.json().catch(() => ({}));
      const message = extractErrorDetail(data, 'Scan not found for AI guidance.');
      throw new RecommendationApiError(404, message, true);
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const message = extractErrorDetail(data, `Server error (HTTP ${response.status})`);
      throw new RecommendationApiError(response.status, message, false);
    }

    const data = await response.json();
    return data as ClaudeGuidanceResponse;
  } catch (err: any) {
    if (err instanceof RecommendationApiError || err?.name === 'RecommendationApiError') {
      throw err;
    }

    const isAborted =
      err?.name === 'AbortError' ||
      err?.name === 'CanceledError' ||
      (typeof err?.message === 'string' &&
        (err.message.includes('canceled') || err.message.includes('aborted'))) ||
      controller.signal.aborted ||
      Boolean(signal?.aborted);

    if (isAborted) {
      if (signal?.aborted) {
        throw new RecommendationApiError(null, 'Request was canceled.');
      }
      throw new RecommendationApiError(null, 'Connection timed out. Please try again.');
    }

    console.error('[RECOMMENDATION API] AI guidance fetch error:', err);
    throw new RecommendationApiError(null, 'Unable to connect to server. Please check your connection.');
  } finally {
    clearTimeout(timeoutId);
    if (signal) {
      signal.removeEventListener('abort', onExternalAbort);
    }
  }
}

