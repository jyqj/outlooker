import { useTranslation } from 'react-i18next';
import { Copy, Check, AlertCircle } from 'lucide-react';
import { Button } from './ui/Button';
import { useCopyToClipboard } from '@/hooks';

interface VerificationCodeCardProps {
  code?: string | null;
  showFallback?: boolean;
}

/**
 * 验证码高亮展示卡片组件
 * - 大字号显示验证码
 * - 支持点击整体或按钮复制
 * - 展示复制成功/失败提示
 */
export default function VerificationCodeCard({ code, showFallback = false }: VerificationCodeCardProps) {
  const { t } = useTranslation();
  const { copy, copied, error: copyError } = useCopyToClipboard(2000);

  const handleCopy = async () => {
    if (!code) return;
    await copy(code);
  };

  const hasCode = Boolean(code);

  return (
    <div className="bg-gradient-to-br from-primary/5 to-accent/5 p-6 rounded-xl border-2 border-primary shadow-lg">
      <h4 className="text-sm font-bold text-primary uppercase tracking-wide mb-4 text-center">
        {hasCode ? t('verification.code.detected') : t('verification.code.notDetected')}
      </h4>
      {hasCode ? (
        <div
          role="button"
          tabIndex={0}
          className="flex items-center justify-center gap-3 cursor-pointer group bg-card p-5 rounded-lg hover:shadow-md active:scale-[0.98] active:shadow-sm transition-all duration-150 border-2 border-primary"
          onClick={handleCopy}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleCopy(); } }}
          aria-label={t('verification.code.copyLabel', { code })}
          title={t('verification.code.clickToCopy')}
        >
          <span className="text-5xl md:text-6xl font-mono font-black tracking-wider text-primary select-all">
            {code}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full hover:bg-primary/20 shrink-0"
          >
            {copied ? (
              <Check className="w-6 h-6 text-success" />
            ) : (
              <Copy className="w-6 h-6 text-primary" />
            )}
          </Button>
        </div>
      ) : (
        showFallback && (
          <div className="text-center py-4">
            <p className="text-muted-foreground">{t('verification.code.notRecognized')}</p>
            <p className="text-sm text-muted-foreground mt-1">{t('verification.code.checkBelow')}</p>
          </div>
        )
      )}
      {copied && (
        <p className="text-center text-sm text-success mt-3 font-semibold animate-in fade-in duration-200">
          ✓ {t('verification.code.copied')}
        </p>
      )}
      {copyError && (
        <div className="flex items-center justify-center gap-2 mt-3 text-sm text-warning font-medium animate-in fade-in duration-200">
          <AlertCircle className="w-4 h-4" />
          <span>{t('verification.code.copyFailed')}</span>
        </div>
      )}
    </div>
  );
}
