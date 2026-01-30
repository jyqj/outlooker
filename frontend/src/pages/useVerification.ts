import { useState, type FormEvent } from 'react';
import api from '@/lib/api';
import { extractCodeFromMessage, logError } from '@/lib/utils';
import { handleApiError } from '@/lib/error';
import type { Email, ApiResponse } from '@/types';
import type { EmailResult } from '@/components/VerificationResultCard';

export function useVerification() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EmailResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: FormEvent, forceRefresh = false) => {
    if (e) e.preventDefault();
    if (!email) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const params: Record<string, unknown> = { email, page_size: 1, page: 1 };
      if (forceRefresh) {
        params.refresh = true;
      }
      const response = await api.get<ApiResponse<Email[] | { items: Email[] }>>('/api/messages', {
        params
      });

      if (response.data.success) {
        const payload = response.data.data;
        const messages = Array.isArray(payload) ? payload : payload?.items;
        if (messages && messages.length > 0) {
          const msg = messages[0];
          const code = extractCodeFromMessage(msg);

          setResult({
            ...msg,
            extractedCode: code
          });
        } else {
          setError('该邮箱暂无邮件');
        }
      } else {
        setError(response.data?.message || '获取失败');
      }
    } catch (err: unknown) {
      setError(handleApiError(err, '获取验证码失败', '网络请求失败，请检查邮箱地址是否正确'));
    } finally {
      setLoading(false);
    }
  };

  const handleAutoOtp = async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const unusedRes = await api.get<ApiResponse<{ email: string }>>('/api/public/account-unused');
      const unusedPayload = unusedRes.data;

      if (!unusedPayload?.success || !unusedPayload?.data?.email) {
        setError(unusedPayload?.message || '暂无可用邮箱，请稍后重试');
        return;
      }

      const autoEmail = unusedPayload.data.email;
      setEmail(autoEmail);

      const otpRes = await api.get<ApiResponse<{ code: string }>>(
        `/api/public/account/${encodeURIComponent(autoEmail)}/otp`,
      );
      const otpPayload = otpRes.data;

      if (!otpPayload?.success || !otpPayload?.data?.code) {
        setError(otpPayload?.message || '未自动识别到验证码');
        return;
      }

      const code = otpPayload.data.code;

      setResult({
        id: 'auto',
        subject: '(自动接码)',
        body: { content: '', contentType: 'text' },
        bodyPreview: '',
        sender: { emailAddress: { name: 'Outlooker', address: '' } },
        receivedDateTime: new Date().toISOString(),
        extractedCode: code,
      });

      try {
        await api.post(
          `/api/public/account/${encodeURIComponent(autoEmail)}/used`,
        );
      } catch (markErr) {
        logError('标记邮箱为已使用失败', markErr);
      }
    } catch (err: unknown) {
      setError(handleApiError(err, '自动获取验证码失败', '自动获取验证码失败，请稍后重试'));
    } finally {
      setLoading(false);
    }
  };

  return {
    email,
    setEmail,
    loading,
    result,
    error,
    handleSearch,
    handleAutoOtp,
  };
}
