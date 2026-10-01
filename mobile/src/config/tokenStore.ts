/**
 * Token Storage — persists and retrieves the JWT access token.
 *
 * Uses expo-file-system (same pattern as LanguageContext) since no
 * SecureStore or AsyncStorage is installed in this project.
 *
 * Token is written on login/register success and read on scan upload.
 * On web, falls back to localStorage.
 *
 * Security note: This uses the document directory which is app-private
 * on both Android and iOS — not accessible to other apps.
 */

import * as FileSystem from 'expo-file-system/legacy';
import { Platform } from 'react-native';

const TOKEN_FILENAME = 'tursathi_auth_token.txt';

const TOKEN_PATH = (() => {
  const base = FileSystem.documentDirectory || FileSystem.cacheDirectory || '';
  return `${base}${TOKEN_FILENAME}`;
})();

export async function saveAuthToken(token: string): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('tursathi_auth_token', token);
      }
      return;
    }
    await FileSystem.writeAsStringAsync(TOKEN_PATH, token, {
      encoding: FileSystem.EncodingType.UTF8,
    });
  } catch (err) {
    console.warn('[TokenStore] Failed to save auth token:', err);
  }
}

export async function getAuthToken(): Promise<string | null> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem('tursathi_auth_token') || null;
      }
      return null;
    }
    const info = await FileSystem.getInfoAsync(TOKEN_PATH);
    if (!info.exists) return null;
    const token = await FileSystem.readAsStringAsync(TOKEN_PATH, {
      encoding: FileSystem.EncodingType.UTF8,
    });
    return token.trim() || null;
  } catch (err) {
    console.warn('[TokenStore] Failed to read auth token:', err);
    return null;
  }
}

export async function clearAuthToken(): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem('tursathi_auth_token');
      }
      return;
    }
    const info = await FileSystem.getInfoAsync(TOKEN_PATH);
    if (info.exists) {
      await FileSystem.deleteAsync(TOKEN_PATH, { idempotent: true });
    }
  } catch (err) {
    console.warn('[TokenStore] Failed to clear auth token:', err);
  }
}
