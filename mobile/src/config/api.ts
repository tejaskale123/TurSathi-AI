import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Default API URL configuration
// Dynamically resolves current laptop LAN IP for physical mobile devices via Expo Go
export const getBaseUrl = (): string => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  if (Platform.OS === 'web') {
    if (typeof window !== 'undefined' && window.location && window.location.hostname) {
      return `http://${window.location.hostname}:8000`;
    }
    return 'http://localhost:8000';
  }
  // Dynamically derive laptop LAN IP from Expo Go metadata properties
  const candidateHostUris = [
    Constants.expoConfig?.hostUri,
    Constants.manifest2?.extra?.expoGo?.debuggerHost,
    (Constants as any).manifest2?.extra?.expoGo?.developer?.tool,
    (Constants as any).manifest?.debuggerHost,
    (Constants as any).linkingUri,
    (Constants as any).experienceUrl,
  ];

  for (const rawHostUri of candidateHostUris) {
    if (rawHostUri && typeof rawHostUri === 'string') {
      const cleanUri = rawHostUri.replace(/^(exp|http|https):\/\//, '');
      const lanIp = cleanUri.split(':')[0];
      if (
        lanIp &&
        lanIp !== 'localhost' &&
        lanIp !== '127.0.0.1' &&
        lanIp !== '0.0.0.0'
      ) {
        return `http://${lanIp}:8000`;
      }
    }
  }
  return 'http://10.211.50.75:8000';
};

export const API_BASE_URL = getBaseUrl();

export const getApiKey = (): string | undefined => {
  return process.env.EXPO_PUBLIC_API_KEY;
};

export const getHeaders = (customHeaders?: Record<string, string>): Record<string, string> => {
  const headers: Record<string, string> = {
    ...customHeaders,
  };
  const apiKey = getApiKey();
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  return headers;
};

export interface UserResponse {
  id: string;
  full_name: string;
  mobile_number: string;
  email?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface RegisterPayload {
  full_name: string;
  mobile_number: string;
  email?: string;
  password: string;
  confirm_password: string;
}

export interface LoginPayload {
  identifier: string;
  password: string;
}

const FETCH_TIMEOUT_MS = 15000;

export function extractErrorDetail(data: any, fallback: string): string {
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

export async function registerUser(payload: RegisterPayload): Promise<AuthTokenResponse> {
  const baseUrl = getBaseUrl();
  console.log(`[MOBILE AUTH] Sending Register request to: ${baseUrl}/api/v1/auth/register`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new Error('Connection timed out. Please check your connection and try again.');
    }
    throw new Error('Unable to connect to server. Please check your connection and try again.');
  } finally {
    clearTimeout(timeoutId);
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMessage = extractErrorDetail(data, 'Registration failed. Please try again.');
    throw new Error(errorMessage);
  }

  if (!data?.access_token || !data?.user) {
    throw new Error('Invalid authentication response from server.');
  }

  return data as AuthTokenResponse;
}

export async function loginUser(payload: LoginPayload): Promise<AuthTokenResponse> {
  const baseUrl = getBaseUrl();
  console.log(`[MOBILE AUTH] Sending Login request to: ${baseUrl}/api/v1/auth/login`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (_netErr: any) {
    if (_netErr?.name === 'AbortError') {
      throw new Error('Connection timed out. Please check your connection and try again.');
    }
    throw new Error('Unable to connect to server. Please check your connection and try again.');
  } finally {
    clearTimeout(timeoutId);
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 || response.status === 400) {
      throw new Error(extractErrorDetail(data, 'Invalid mobile number/email or password.'));
    }
    const errorMessage = extractErrorDetail(data, `Server returned HTTP ${response.status}.`);
    throw new Error(errorMessage);
  }

  if (!data.access_token || !data.user) {
    throw new Error('Invalid authentication response from server.');
  }

  return data as AuthTokenResponse;
}

export async function exchangeGoogleCode(code: string): Promise<AuthTokenResponse> {
  const baseUrl = getBaseUrl();
  console.log(`[MOBILE AUTH] Exchanging Google Code at: ${baseUrl}/api/v1/auth/google/exchange`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/google/exchange`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ exchange_code: code }),
      signal: controller.signal,
    });
  } catch (_netErr) {
    throw new Error('Unable to connect to server. Please check your connection and try again.');
  } finally {
    clearTimeout(timeoutId);
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || 'Google authentication failed.');
  }

  if (!data.access_token || !data.user) {
    throw new Error('Invalid authentication response from server.');
  }

  return data as AuthTokenResponse;
}
