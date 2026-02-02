import { useState } from 'react';
import { Eye, EyeOff, Copy, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { useCopyToClipboard } from '@/hooks';
import { showSuccess, showError } from '@/lib/toast';
import { logError } from '@/lib/utils';
import type { CredentialsDisplayProps } from './types';

/**
 * 凭证信息展示组件
 * 展示密码和 Refresh Token，支持显示/隐藏和复制功能
 */
export default function CredentialsDisplay({
  result,
  showCredentials,
  onToggleShow,
}: CredentialsDisplayProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const { copy } = useCopyToClipboard(2000);

  // Copy to clipboard
  const handleCopy = async (text: string, field: string) => {
    const success = await copy(text);
    if (success) {
      setCopiedField(field);
      showSuccess('已复制到剪贴板');
      setTimeout(() => setCopiedField(null), 2000);
    } else {
      showError('复制失败');
      logError('Copy failed', new Error('Copy operation failed'));
    }
  };

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-muted-foreground">凭证信息</label>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleShow}
          className="gap-1 h-7"
        >
          {showCredentials ? (
            <>
              <EyeOff className="w-3.5 h-3.5" />
              隐藏
            </>
          ) : (
            <>
              <Eye className="w-3.5 h-3.5" />
              显示
            </>
          )}
        </Button>
      </div>

      {/* Password */}
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">密码</label>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-muted p-2 rounded font-mono text-xs break-all">
            {showCredentials ? (result.password || '(空)') : '••••••••'}
          </div>
          {result.password && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleCopy(result.password!, 'password')}
            >
              {copiedField === 'password' ? (
                <Check className="w-3.5 h-3.5 text-success" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Refresh Token */}
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">Refresh Token</label>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-muted p-2 rounded font-mono text-xs break-all max-h-20 overflow-auto">
            {showCredentials
              ? result.refresh_token
                ? result.refresh_token.length > 50
                  ? result.refresh_token.slice(0, 50) + '...'
                  : result.refresh_token
                : '(空)'
              : '••••••••••••••••'}
          </div>
          {result.refresh_token && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleCopy(result.refresh_token!, 'refresh_token')}
            >
              {copiedField === 'refresh_token' ? (
                <Check className="w-3.5 h-3.5 text-success" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
