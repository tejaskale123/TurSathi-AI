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
