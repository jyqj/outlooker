import { useState } from 'react';
import { Copy, Check, AlertCircle } from 'lucide-react';
import { Button } from './ui/Button';

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
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);

  const handleCopy = async () => {
    if (!code) return;
    
    try {
      // 优先使用 Clipboard API
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(code);
      } else {
        // 降级方案：使用 execCommand
        const textArea = document.createElement('textarea');
        textArea.value = code;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        textArea.style.top = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const success = document.execCommand('copy');
        document.body.removeChild(textArea);
        if (!success) {
          throw new Error('execCommand copy failed');
        }
      }
      setCopied(true);
      setCopyError(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
      setCopyError(true);
      setTimeout(() => setCopyError(false), 3000);
    }
  };

  const hasCode = Boolean(code);

  return (
    <div className="bg-gradient-to-br from-primary/5 to-accent/5 p-6 rounded-xl border-2 border-primary shadow-lg">
      <h4 className="text-sm font-bold text-primary uppercase tracking-wide mb-4 text-center">
        {hasCode ? '🔐 检测到的验证码' : '🔍 暂未检测到验证码'}
      </h4>
      {hasCode ? (
        <div
          className="flex items-center justify-center gap-3 cursor-pointer group bg-card p-5 rounded-lg hover:shadow-md transition-all border-2 border-primary"
          onClick={handleCopy}
          title="点击复制验证码"
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
            <p className="text-muted-foreground">未自动识别到验证码</p>
            <p className="text-sm text-muted-foreground mt-1">请查看下方邮件正文</p>
          </div>
        )
      )}
      {copied && (
        <p className="text-center text-sm text-success mt-3 font-semibold animate-in fade-in duration-200">
          ✓ 已复制到剪贴板
        </p>
      )}
      {copyError && (
        <div className="flex items-center justify-center gap-2 mt-3 text-sm text-warning font-medium animate-in fade-in duration-200">
          <AlertCircle className="w-4 h-4" />
          <span>复制失败，请手动选择复制</span>
        </div>
      )}
    </div>
  );
}
