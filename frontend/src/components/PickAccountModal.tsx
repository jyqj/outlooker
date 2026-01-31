import { useState, useEffect } from 'react';
import { 
  Shuffle, 
  Copy, 
  Check, 
  X, 
  Plus, 
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff
} from 'lucide-react';
import { Dialog } from './ui/Dialog';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Badge } from './ui/Badge';
import api from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';
import { logError } from '@/lib/utils';

interface PickAccountModalProps {
  isOpen: boolean;
  preselectedTag?: string;
  availableTags?: string[];
  onClose: () => void;
  onSuccess?: () => void;
}

interface PickResult {
  email: string;
  tags: string[];
  password?: string;
  refresh_token?: string;
  client_id?: string;
}

type ModalStep = 'input' | 'result';

export default function PickAccountModal({
  isOpen,
  preselectedTag = '',
  availableTags = [],
  onClose,
  onSuccess,
}: PickAccountModalProps) {
  // Form state
  const [tag, setTag] = useState(preselectedTag);
  const [excludeTags, setExcludeTags] = useState<string[]>([]);
  const [newExcludeTag, setNewExcludeTag] = useState('');
  const [returnCredentials, setReturnCredentials] = useState(false);
  const [showCredentials, setShowCredentials] = useState(false);
  
  // UI state
  const [step, setStep] = useState<ModalStep>('input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PickResult | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setTag(preselectedTag);
      setExcludeTags([]);
      setNewExcludeTag('');
      setReturnCredentials(false);
      setShowCredentials(false);
      setStep('input');
      setLoading(false);
      setError(null);
      setResult(null);
      setCopied(null);
    }
  }, [isOpen, preselectedTag]);

  // Add exclude tag
  const handleAddExcludeTag = () => {
    const trimmed = newExcludeTag.trim();
    if (trimmed && !excludeTags.includes(trimmed)) {
      setExcludeTags([...excludeTags, trimmed]);
      setNewExcludeTag('');
    }
  };

  // Remove exclude tag
  const handleRemoveExcludeTag = (tagToRemove: string) => {
    setExcludeTags(excludeTags.filter(t => t !== tagToRemove));
  };

  // Submit pick request
  const handlePick = async () => {
    if (!tag.trim()) {
      setError('请输入要打的标签');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post<{ success: boolean; data?: PickResult; message?: string }>(
        '/api/accounts/pick',
        {
          tag: tag.trim(),
          exclude_tags: excludeTags,
          return_credentials: returnCredentials,
        }
      );

      if (response.data.success && response.data.data) {
        setResult(response.data.data);
        setStep('result');
        showSuccess(response.data.message || '取号成功');
        onSuccess?.();
      } else {
        setError(response.data.message || '取号失败');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error 
        ? err.message 
        : (err as { response?: { data?: { message?: string } } })?.response?.data?.message || '取号失败，请稍后重试';
      setError(errorMessage);
      logError('Pick account failed', err);
    } finally {
      setLoading(false);
    }
  };

  // Copy to clipboard
  const handleCopy = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(field);
      showSuccess('已复制到剪贴板');
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      showError('复制失败');
      logError('Copy failed', err);
    }
  };

  // Continue picking
  const handleContinue = () => {
    setStep('input');
    setResult(null);
    setError(null);
  };

  // Close modal
  const handleClose = () => {
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title={step === 'input' ? '随机取号' : '取号成功'}
      className="max-w-md"
    >
      {step === 'input' ? (
        <div className="space-y-5 py-2">
          {/* Tag Input */}
          <div className="space-y-2">
            <label htmlFor="target-tag-input" className="text-sm font-medium">
              目标标签 <span className="text-destructive" aria-hidden="true">*</span>
              <span className="sr-only">（必填）</span>
            </label>
            <div className="relative">
              <Input
                id="target-tag-input"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                placeholder="输入要打的标签，如: 注册-Apple"
                list="available-tags"
                required
                aria-describedby="target-tag-hint"
              />
              {availableTags.length > 0 && (
                <datalist id="available-tags">
                  {availableTags.map((t) => (
                    <option key={t} value={t} />
                  ))}
                </datalist>
              )}
            </div>
            <p id="target-tag-hint" className="text-xs text-muted-foreground">
              系统会随机选择一个没有此标签的账户，并自动打上该标签
            </p>
          </div>

          {/* Exclude Tags */}
          <div className="space-y-2">
            <label htmlFor="exclude-tag-input" className="text-sm font-medium">排除标签（可选）</label>
            <div className="flex gap-2">
              <Input
                id="exclude-tag-input"
                value={newExcludeTag}
                onChange={(e) => setNewExcludeTag(e.target.value)}
                placeholder="输入要排除的标签"
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddExcludeTag())}
                aria-describedby="exclude-tags-hint"
              />
              <Button
                type="button"
                variant="secondary"
                size="icon"
                onClick={handleAddExcludeTag}
                disabled={!newExcludeTag.trim()}
                aria-label="添加排除标签"
              >
                <Plus className="w-4 h-4" aria-hidden="true" />
              </Button>
            </div>
            {excludeTags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2" role="group" aria-label="已添加的排除标签">
                {excludeTags.map((t) => (
                  <Badge key={t} variant="secondary" className="pl-2 pr-1 py-1 flex items-center gap-1">
                    {t}
                    <button
                      onClick={() => handleRemoveExcludeTag(t)}
                      className="hover:bg-muted-foreground/20 rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-ring rounded"
                      aria-label={`移除排除标签 ${t}`}
                    >
                      <X className="w-3 h-3" aria-hidden="true" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
            <p id="exclude-tags-hint" className="text-xs text-muted-foreground">
              有这些标签的账户不会被选中
            </p>
          </div>

          {/* Return Credentials Option */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="return-credentials"
              checked={returnCredentials}
              onChange={(e) => setReturnCredentials(e.target.checked)}
              className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
            />
            <label htmlFor="return-credentials" className="text-sm">
              同时返回凭证信息（密码、refresh_token）
            </label>
          </div>

          {/* Error Message */}
          {error && (
            <div role="alert" className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-lg">
              <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={handleClose} disabled={loading}>
              取消
            </Button>
            <Button onClick={handlePick} disabled={loading || !tag.trim()} className="gap-1">
              {loading ? (
                <>
                  <Shuffle className="w-4 h-4 animate-spin" />
                  正在取号...
                </>
              ) : (
                <>
                  <Shuffle className="w-4 h-4" />
                  确认取号
                </>
              )}
            </Button>
          </div>
        </div>
      ) : result ? (
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
                {copied === 'email' ? (
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
            <div className="space-y-3 border-t pt-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-muted-foreground">凭证信息</label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCredentials(!showCredentials)}
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
                      {copied === 'password' ? (
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
                      ? (result.refresh_token 
                          ? (result.refresh_token.length > 50 
                              ? result.refresh_token.slice(0, 50) + '...' 
                              : result.refresh_token)
                          : '(空)')
                      : '••••••••••••••••'}
                  </div>
                  {result.refresh_token && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleCopy(result.refresh_token!, 'refresh_token')}
                    >
                      {copied === 'refresh_token' ? (
                        <Check className="w-3.5 h-3.5 text-success" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={handleClose}>
              关闭
            </Button>
            <Button onClick={handleContinue} className="gap-1">
              <Shuffle className="w-4 h-4" />
              继续取号
            </Button>
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}
