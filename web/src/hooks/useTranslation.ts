/**
 * useTranslation — single source of truth for the Spanish toggle.
 *
 * Pattern: pass an English string as the key. Returns the Spanish translation
 * when locale='es', the English original (or your `fallback`) otherwise.
 *
 * Interpolation: pass a values map as the second arg; placeholders are
 * `{name}` style (e.g., 'Welcome {firstName}!'). Missing values are left
 * as-is so partial replacements don't blow up.
 */
import { useCallback, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import translations, { type Locale } from '../i18n/translations';

function interpolate(template: string, values?: Record<string, string | number>): string {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    const v = values[key];
    return v === undefined || v === null ? `{${key}}` : String(v);
  });
}

export function useTranslation() {
  const { locale: userLocale } = useAuth();
  const locale: Locale = userLocale === 'es' ? 'es' : 'en';

  const t = useCallback(
    (key: string, values?: Record<string, string | number>): string => {
      const translated = locale === 'es' ? translations.es[key] : undefined;
      return interpolate(translated ?? key, values);
    },
    [locale],
  );

  return useMemo(() => ({ t, locale, isEs: locale === 'es' }), [t, locale]);
}
