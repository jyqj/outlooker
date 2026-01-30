import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import zhCN from './locales/zh-CN.json';
import en from './locales/en.json';

// Get saved language or detect from browser
const getDefaultLanguage = (): string => {
    const saved = localStorage.getItem('language');
    if (saved && ['zh-CN', 'en'].includes(saved)) {
        return saved;
    }
    // Detect from browser
    const browserLang = navigator.language;
    if (browserLang.startsWith('zh')) {
        return 'zh-CN';
    }
    return 'en';
};

i18n
    .use(initReactI18next)
    .init({
        resources: {
            'zh-CN': { translation: zhCN },
            'en': { translation: en },
        },
        lng: getDefaultLanguage(),
        fallbackLng: 'zh-CN',
        interpolation: {
            escapeValue: false, // React already escapes
        },
        react: {
            useSuspense: false,
        },
    });

export default i18n;

// Helper to change language
export const changeLanguage = (lang: string): void => {
    localStorage.setItem('language', lang);
    i18n.changeLanguage(lang);
};

export const supportedLanguages = [
    { code: 'zh-CN', name: '中文' },
    { code: 'en', name: 'English' },
] as const;
