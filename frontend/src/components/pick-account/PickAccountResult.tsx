import { useState } from 'react';
import { Shuffle, Copy, Check, CheckCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useCopyToClipboard } from '@/hooks';
import { showSuccess, showError } from '@/lib/toast';
import { logError } from '@/lib/utils';
import CredentialsDisplay from './CredentialsDisplay';
import type { PickAccountResultProps } from './types';

/**
 * 取号结果展示组件
 * 显示取号成功后的邮箱、标签和可选的凭证信息
 */
export default function PickAccountResult({
  result,
  returnCredentials,
  onPickAnother,
  onClose,
}: PickAccountResultProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [showCredentials, setShowCredentials] = useState(false);
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
    <div className="space-y-5 py-2">
      {/* Success Icon */}
      <div className="flex justify-center">
        <div className="w-16 h-16 rounded-full bg-success/10 flex items-center justify-center">
          <CheckCircle className="w-8 h-8 text-success" />
        </div>
      </div>

      {/* Email */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">邮箱地址</label>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-muted p-3 rounded-lg font-mono text-sm break-all">
            {result.email}
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={() => handleCopy(result.email, 'email')}
          >
            {copiedField === 'email' ? (
              <Check className="w-4 h-4 text-success" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Tags */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">已标记</label>
        <div className="flex flex-wrap gap-1.5">
          {result.tags.map((t) => (
            <Badge key={t} variant="default">
              {t}
            </Badge>
          ))}
        </div>
      </div>

      {/* Credentials (if returned) */}
      {returnCredentials && result.password !== undefined && (
        <CredentialsDisplay
          result={result}
          showCredentials={showCredentials}
          onToggleShow={() => setShowCredentials(!showCredentials)}
        />
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="outline" onClick={onClose}>
          关闭
        </Button>
        <Button onClick={onPickAnother} className="gap-1">
          <Shuffle className="w-4 h-4" />
          继续取号
        </Button>
      </div>
    </div>
  );
}
