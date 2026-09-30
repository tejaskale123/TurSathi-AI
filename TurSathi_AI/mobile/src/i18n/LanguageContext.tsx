import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import {
  Language,
  translate,
  translateDiseaseName,
  translateSeverity,
} from './translations';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  tDisease: (name?: string) => string;
  tSeverity: (severity?: string) => string;
  isReady: boolean;
}

const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  setLanguage: () => {},
  t: (k) => k,
  tDisease: (n) => n || '',
  tSeverity: (s) => s || '',
  isReady: false,
});

const STORAGE_FILE = `${FileSystem.documentDirectory || FileSystem.cacheDirectory || ''}tursathi_language_setting.txt`;

// Read persisted language from file system or local storage
async function readStoredLanguage(): Promise<Language | null> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        const val = window.localStorage.getItem('tursathi_language');
        if (val === 'en' || val === 'mr' || val === 'hi') {
          return val;
        }
      }
      return null;
    }

    const fileInfo = await FileSystem.getInfoAsync(STORAGE_FILE);
    if (fileInfo.exists) {
      const content = await FileSystem.readAsStringAsync(STORAGE_FILE, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      const trimmed = content.trim();
      if (trimmed === 'en' || trimmed === 'mr' || trimmed === 'hi') {
        return trimmed as Language;
      }
    }
  } catch (err) {
    console.warn('[LanguageContext] Error reading saved language:', err);
  }
  return null;
}

// Persist chosen language to file system or local storage
async function writeStoredLanguage(lang: Language): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('tursathi_language', lang);
      }
      return;
    }

    await FileSystem.writeAsStringAsync(STORAGE_FILE, lang, {
      encoding: FileSystem.EncodingType.UTF8,
    });
  } catch (err) {
    console.warn('[LanguageContext] Error saving language:', err);
  }
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>('en');
  const [isReady, setIsReady] = useState(false);

  // Load language preference on startup
  useEffect(() => {
    let isMounted = true;
    readStoredLanguage()
      .then((saved) => {
        if (isMounted && saved) {
          setLanguageState(saved);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsReady(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Update language globally and persist immediately
  const setLanguage = useCallback((newLang: Language) => {
    setLanguageState(newLang);
    void writeStoredLanguage(newLang);
  }, []);

  // Translation helper
  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      return translate(language, key, params);
    },
    [language]
  );

  // Disease name translation helper
  const tDisease = useCallback(
    (name?: string) => {
      return translateDiseaseName(name, language);
    },
    [language]
  );

  // Severity translation helper
  const tSeverity = useCallback(
    (severity?: string) => {
      return translateSeverity(severity, language);
    },
    [language]
  );

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t,
        tDisease,
        tSeverity,
        isReady,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

// Custom hook to consume language state
export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
