import { useState, useEffect } from 'react';
import { Dialog } from '../ui/Dialog';
import api from '@/lib/api';
import { showSuccess } from '@/lib/toast';
import { handleApiError } from '@/lib/error';
import PickAccountForm from './PickAccountForm';
import PickAccountResult from './PickAccountResult';
import type { PickAccountModalProps, PickResult, ModalStep } from './types';

/**
 * 取号 Modal 主容器组件
 * 负责状态管理和子组件编排
 */
export default function PickAccountModal({
  isOpen,
  preselectedTag = '',
  availableTags = [],
  onClose,
  onSuccess,
}: PickAccountModalProps) {
  // Form state
  const [tag, setTag] = useState(preselectedTag);
  const [isCustomTag, setIsCustomTag] = useState(false);
  const [customTag, setCustomTag] = useState('');
  const [excludeTags, setExcludeTags] = useState<string[]>([]);
  const [newExcludeTag, setNewExcludeTag] = useState('');
  const [returnCredentials, setReturnCredentials] = useState(false);

  // UI state
  const [step, setStep] = useState<ModalStep>('input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PickResult | null>(null);

  // Get the actual tag value (either selected or custom)
  const effectiveTag = isCustomTag ? customTag : tag;

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setTag(preselectedTag);
      setIsCustomTag(!preselectedTag && availableTags.length === 0);
      setCustomTag('');
      setExcludeTags([]);
      setNewExcludeTag('');
      setReturnCredentials(false);
      setStep('input');
      setLoading(false);
      setError(null);
      setResult(null);
    }
  }, [isOpen, preselectedTag, availableTags.length]);

  // Validate current tag when availableTags changes
  useEffect(() => {
    if (!isCustomTag && tag && availableTags.length > 0 && !availableTags.includes(tag)) {
      // Current tag is no longer valid, reset to empty or preselectedTag
      setTag(preselectedTag || '');
      if (!preselectedTag && availableTags.length > 0) {
        setIsCustomTag(false);
      }
    }
  }, [availableTags, tag, isCustomTag, preselectedTag]);

  // Submit pick request
  const handlePick = async () => {
    if (!effectiveTag.trim()) {
      setError('请选择或输入要打的标签');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post<{ success: boolean; data?: PickResult; message?: string }>(
        '/api/accounts/pick',
        {
          tag: effectiveTag.trim(),
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
      setError(handleApiError(err, '取号失败', '取号失败，请稍后重试'));
    } finally {
      setLoading(false);
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
        <PickAccountForm
          effectiveTag={effectiveTag}
          isCustomTag={isCustomTag}
          customTag={customTag}
          tag={tag}
          excludeTags={excludeTags}
          newExcludeTag={newExcludeTag}
          returnCredentials={returnCredentials}
          availableTags={availableTags}
          loading={loading}
          error={error}
          onTagChange={setTag}
          onCustomTagChange={setCustomTag}
          onIsCustomTagChange={setIsCustomTag}
          onExcludeTagsChange={setExcludeTags}
          onNewExcludeTagChange={setNewExcludeTag}
          onReturnCredentialsChange={setReturnCredentials}
          onSubmit={handlePick}
          onCancel={handleClose}
        />
      ) : result ? (
        <PickAccountResult
          result={result}
          returnCredentials={returnCredentials}
          onPickAnother={handleContinue}
          onClose={handleClose}
        />
      ) : null}
    </Dialog>
  );
}
