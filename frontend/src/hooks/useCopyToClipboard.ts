import { useState, useCallback } from 'react';

/**
 * 复制文本到剪贴板的 hook
 * @param timeout - 复制成功状态持续时间（毫秒），默认 2000
 */
export function useCopyToClipboard(timeout = 2000) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);

  const copy = useCallback(async (text: string): Promise<boolean> => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // 降级方案：使用 execCommand
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setError(false);
      setTimeout(() => setCopied(false), timeout);
      return true;
    } catch {
      setError(true);
      setCopied(false);
      setTimeout(() => setError(false), timeout + 1000);
      return false;
    }
  }, [timeout]);

  const reset = useCallback(() => {
    setCopied(false);
    setError(false);
  }, []);

  return { copy, copied, error, reset };
}
