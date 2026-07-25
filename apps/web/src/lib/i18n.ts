/**
 * Internationalisation (i18n) layer.
 *
 * Lightweight translation helper. Replace with react-i18next or similar
 * when the string catalogue grows beyond scaffolding.
 */

export type Locale = 'en';

const DEFAULT_LOCALE: Locale = 'en';

const messages: Record<Locale, Record<string, string>> = {
  en: {
    'app.title': 'Odysseus',
    'app.tagline': 'AI-assisted research and writing',
    'nav.label': 'Main navigation',
    'nav.home': 'Home',
    'nav.chat': 'Chat',
    'nav.documents': 'Documents',
    'nav.settings': 'Settings',
    'home.heading': 'Welcome to Odysseus',
    'home.body': 'Your AI-assisted research and writing companion.',
    'chat.heading': 'Chat',
    'documents.heading': 'Documents',
    'settings.heading': 'Settings',
    'footer.credit': 'Odysseus — AI-assisted research and writing',
    'error.rootNotFound': 'Root element #root not found in the document.',
  },
};

export function t(key: keyof typeof messages['en'], locale: Locale = DEFAULT_LOCALE): string {
  return messages[locale]?.[key] ?? key;
}

/**
 * Currently active locale. Hard-coded to 'en' — expand when multi-locale is needed.
 */
export function useLocale(): Locale {
  return DEFAULT_LOCALE;
}
