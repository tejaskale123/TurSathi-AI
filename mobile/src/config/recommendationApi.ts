import { getBaseUrl } from './api';

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

export class RecommendationApiError extends Error {
  constructor(
    public readonly httpStatus: number | null,
    message: string,
    public readonly isNotFound: boolean = false,
  ) {
    super(message);
    this.name = 'RecommendationApiError';
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
      headers,
      signal: controller.signal,
    });

    if (response.status === 404) {
      const data = await response.json().catch(() => ({}));
      throw new RecommendationApiError(
        404,
        data.detail || 'Verified spray guidance is not available for this condition yet.',
        true,
      );
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new RecommendationApiError(
        response.status,
        data.detail || `Server error (HTTP ${response.status})`,
        false,
      );
    }

    const data = await response.json();
    return data as SprayGuidanceResponse;
  } catch (err: any) {
    if (err instanceof RecommendationApiError) {
      throw err;
    }
    if (err?.name === 'AbortError') {
      throw new RecommendationApiError(null, 'Connection timed out. Please try again.');
    }
    throw new RecommendationApiError(null, 'Unable to connect to server. Please check your connection.');
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchAIGuidance(
  scanId: number,
  language: string,
  token?: string,
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
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      signal: controller.signal,
    });

    if (response.status === 404) {
      const data = await response.json().catch(() => ({}));
      throw new RecommendationApiError(
        404,
        data.detail || 'Scan not found for AI guidance.',
        true,
      );
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new RecommendationApiError(
        response.status,
        data.detail || `Server error (HTTP ${response.status})`,
        false,
      );
    }

    const data = await response.json();
    return data as ClaudeGuidanceResponse;
  } catch (err: any) {
    if (err instanceof RecommendationApiError) {
      throw err;
    }
    if (err?.name === 'AbortError') {
      throw new RecommendationApiError(null, 'Connection timed out. Please try again.');
    }
    throw new RecommendationApiError(null, 'Unable to connect to server. Please check your connection.');
  } finally {
    clearTimeout(timeoutId);
  }
}

