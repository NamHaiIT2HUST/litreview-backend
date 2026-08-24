import React, { createContext, useContext, useState, useEffect } from 'react';
import enTranslations from '../locales/en.json';
import viTranslations from '../locales/vi.json';

const translations = {
  en: enTranslations,
  vi: viTranslations,
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('litreview_language') || 'vi';
  });

  useEffect(() => {
    localStorage.setItem('litreview_language', language);
  }, [language]);

  const t = (key, params = {}) => {
    const keys = key.split('.');
    let value = translations[language];
    for (const k of keys) {
      if (value === undefined) break;
      value = value[k];
    }
    
    // Fallback to Vietnamese if not found in current language, then to the key itself
    if (value === undefined && language !== 'vi') {
      let fallbackValue = translations['vi'];
      for (const k of keys) {
        if (fallbackValue === undefined) break;
        fallbackValue = fallbackValue[k];
      }
      if (fallbackValue !== undefined) value = fallbackValue;
    }

    let result = value !== undefined ? value : key;

    if (typeof result === 'string' && params && typeof params === 'object') {
      Object.entries(params).forEach(([paramKey, paramVal]) => {
        result = result.replace(
          new RegExp(`\\{${paramKey}\\}`, 'g'),
          paramVal !== undefined && paramVal !== null ? paramVal : ''
        );
      });
    }

    return result;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
