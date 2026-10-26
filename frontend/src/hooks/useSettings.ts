import { useState, useEffect } from 'react';

export interface PebbleSettings {
  stepSpeed: 'slow' | 'normal' | 'fast';
  codeTheme: 'dark' | 'contrast';
  showAsciiGraph: boolean;
  soundEffects: boolean;
}

const DEFAULT_SETTINGS: PebbleSettings = {
  stepSpeed: 'normal',
  codeTheme: 'dark',
  showAsciiGraph: true,
  soundEffects: false,
};

const SETTINGS_KEY = 'pebble_settings';

export function useSettings() {
  const [settings, setSettings] = useState<PebbleSettings>(() => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const raw = window.localStorage.getItem(SETTINGS_KEY);
        if (raw) return JSON.parse(raw);
      }
    } catch {
      // Fallback
    }
    return DEFAULT_SETTINGS;
  });

  useEffect(() => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      }
    } catch {
      // Fail silently
    }
  }, [settings]);

  const updateSetting = <K extends keyof PebbleSettings>(key: K, value: PebbleSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return {
    settings,
    updateSetting,
  };
}
