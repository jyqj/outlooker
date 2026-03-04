import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent } from '@/components/ui/Card';

interface VerificationSearchFormProps {
  email: string;
  onEmailChange: (value: string) => void;
  loading: boolean;
  onSearch: (e?: FormEvent) => void;
}

export function VerificationSearchForm({
  email,
  onEmailChange,
  loading,
  onSearch,
}: VerificationSearchFormProps) {
  const { t } = useTranslation();
  return (
    <Card className="shadow-md">
      <CardContent className="pt-6">
        <form onSubmit={onSearch} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="email"
              className="text-sm font-medium text-foreground flex items-center gap-2"
            >
              <Mail className="w-4 h-4" /> {t('verification.emailLabel')}
            </label>
            <div className="relative">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => onEmailChange(e.target.value)}
                placeholder={t('verification.emailPlaceholder')}
                className={`text-base ${email ? 'pr-10' : ''}`}
                required
                disabled={loading}
              />
              {email && !loading && (
                <button
                  type="button"
                  onClick={() => onEmailChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground transition-all duration-150 hover:bg-muted-foreground/10 hover:text-foreground active:scale-[var(--scale-click-icon)] active:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                  aria-label={t('verification.clearInput')}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col md:flex-row gap-3">
            <Button
              type="submit"
              disabled={loading}
              className="w-full gap-2 text-lg font-semibold py-6 border-2 transition-all"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  {t('verification.fetching')}
                </>
              ) : (
                <>
                  <Mail className="w-6 h-6" />
                  {t('verification.fetchButton')}
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
