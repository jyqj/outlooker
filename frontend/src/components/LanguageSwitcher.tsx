import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { Button } from './ui/Button';
import { changeLanguage, supportedLanguages } from '../i18n';

/**
 * Language Switcher Component
 * Allows users to switch between supported languages
 */
export function LanguageSwitcher() {
    const { i18n } = useTranslation();

    const currentLang = supportedLanguages.find(
        (lang) => lang.code === i18n.language
    );

    const handleChange = () => {
        // Toggle between languages
        const currentIndex = supportedLanguages.findIndex(
            (lang) => lang.code === i18n.language
        );
        const nextIndex = (currentIndex + 1) % supportedLanguages.length;
        changeLanguage(supportedLanguages[nextIndex].code);
    };

    return (
        <Button
            variant="ghost"
            size="sm"
            onClick={handleChange}
            className="flex items-center gap-1.5"
            title={`Switch language / 切换语言`}
        >
            <Globe className="h-4 w-4" />
            <span className="text-sm">{currentLang?.name || 'Language'}</span>
        </Button>
    );
}

export default LanguageSwitcher;
