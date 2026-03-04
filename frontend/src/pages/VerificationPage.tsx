import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, Timer, Square } from 'lucide-react';
import { VerificationSearchForm } from '@/components/VerificationSearchForm';
import { VerificationResultCard } from '@/components/VerificationResultCard';
import { LoadingCard, ErrorCard } from '@/components/StatusCard';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/Button';
import { useVerification } from '@/hooks/useVerification';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

function WaitingIndicator({
  elapsed,
  timeout,
  onStop,
}: {
  elapsed: number;
  timeout: number;
  onStop: () => void;
}) {
  const { t } = useTranslation();
  const pct = Math.min(100, (elapsed / timeout) * 100);
  const remaining = Math.max(0, timeout - elapsed);

  return (
    <div className="bg-card border rounded-xl p-6 text-center space-y-4 animate-in fade-in">
      <div className="relative w-20 h-20 mx-auto">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="36" fill="none" stroke="currentColor" strokeWidth="4" className="text-muted" />
          <circle
            cx="40" cy="40" r="36" fill="none" stroke="currentColor" strokeWidth="4"
            className="text-primary transition-all duration-1000"
            strokeDasharray={`${2 * Math.PI * 36}`}
            strokeDashoffset={`${2 * Math.PI * 36 * (1 - pct / 100)}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-lg font-bold">{remaining}s</span>
      </div>
      <p className="text-sm text-muted-foreground">{t('verification.waiting.message')}</p>
      <Button variant="outline" size="sm" onClick={onStop} className="gap-1.5">
        <Square className="w-3 h-3" /> {t('verification.waiting.stop')}
      </Button>
    </div>
  );
}

export default function VerificationPage() {
  const { t } = useTranslation();
  const {
    email,
    setEmail,
    loading,
    result,
    error,
    handleSearch,
    waiting,
    waitTimeout,
    waitElapsed,
    startWaiting,
    stopWaiting,
  } = useVerification();

  const shortcuts = useMemo(() => ({
    'mod+k': () => {
      const input = document.querySelector<HTMLInputElement>('input[type="email"], input[type="text"]');
      input?.focus();
    },
    'Escape': () => {
      if (waiting) stopWaiting();
    },
  }), [waiting, stopWaiting]);

  useKeyboardShortcuts(shortcuts);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-3xl space-y-6">
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="bg-primary/10 p-3 rounded-lg">
              <Mail className="w-8 h-8 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            {t('verification.title')}
          </h1>
          <p className="text-muted-foreground">
            {t('verification.subtitle')}
          </p>
        </div>

        <VerificationSearchForm
          email={email}
          onEmailChange={setEmail}
          loading={loading || waiting}
          onSearch={handleSearch}
        />

        {/* Wait button - shown when not loading and no result */}
        {!loading && !waiting && !result && email && (
          <div className="flex justify-center">
            <Button variant="outline" onClick={() => startWaiting()} className="gap-2">
              <Timer className="w-4 h-4" /> {t('verification.waiting.start')}
            </Button>
          </div>
        )}

        {/* Waiting indicator */}
        {waiting && (
          <WaitingIndicator elapsed={waitElapsed} timeout={waitTimeout} onStop={stopWaiting} />
        )}

        {loading && !waiting && <LoadingCard message={t('verification.loading')} subMessage={t('verification.loadingSub')} />}

        {error && !loading && !waiting && <ErrorCard error={error} onRetry={() => handleSearch(undefined, true)} />}

        {result && !loading && (
          <VerificationResultCard
            result={result}
            onRefresh={() => handleSearch(undefined, true)}
          />
        )}
      </div>
      <div className="fixed top-4 right-4 z-50 flex items-center gap-1">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
    </div>
  );
}
