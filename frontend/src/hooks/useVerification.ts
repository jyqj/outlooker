import { useState, useRef, useCallback, useEffect, type FormEvent } from 'react';
import api from '@/lib/api';
import { extractCodeFromMessage } from '@/lib/utils';
import { handleApiError } from '@/lib/error';
import type { Email, ApiResponse } from '@/types';
import type { EmailResult } from '@/components/VerificationResultCard';

const POLL_INTERVAL = 3000;
const DEFAULT_TIMEOUT = 120;

export function useVerification() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EmailResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Auto-poll state
  const [waiting, setWaiting] = useState(false);
  const [waitTimeout, setWaitTimeout] = useState(DEFAULT_TIMEOUT);
  const [waitElapsed, setWaitElapsed] = useState(0);
  const waitStartRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (tickRef.current) { clearInterval(tickRef.current); tickRef.current = null; }
  }, []);

  useEffect(() => () => clearTimers(), [clearTimers]);

  const fetchLatest = useCallback(async (forceRefresh = false): Promise<EmailResult | null> => {
    const params: Record<string, unknown> = { email, page_size: 1, page: 1 };
    if (forceRefresh) params.refresh = true;

    const response = await api.get<ApiResponse<Email[] | { items: Email[] }>>('/api/messages', { params });
    if (!response.data.success) return null;

    const payload = response.data.data;
    const messages = Array.isArray(payload) ? payload : payload?.items;
    if (!messages || messages.length === 0) return null;

    const msg = messages[0];
    return { ...msg, extractedCode: extractCodeFromMessage(msg) };
  }, [email]);

  const handleSearch = async (e?: FormEvent, forceRefresh = false) => {
    if (e) e.preventDefault();
    if (!email) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const r = await fetchLatest(forceRefresh);
      if (r) {
        setResult(r);
      } else {
        setError('该邮箱暂无邮件');
      }
    } catch (err: unknown) {
      setError(handleApiError(err, '获取验证码失败', '网络请求失败，请检查邮箱地址是否正确'));
    } finally {
      setLoading(false);
    }
  };

  const notifyUser = useCallback((code: string) => {
    try {
      navigator.clipboard?.writeText(code);
    } catch { /* ignore */ }

    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('验证码已到达', { body: code, icon: '/favicon.ico' });
    }

    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      gain.gain.value = 0.3;
      osc.start();
      osc.stop(ctx.currentTime + 0.15);
    } catch { /* ignore */ }
  }, []);

  const startWaiting = useCallback((timeout = DEFAULT_TIMEOUT) => {
    if (!email || waiting) return;
    setWaiting(true);
    setWaitTimeout(timeout);
    setWaitElapsed(0);
    setError(null);
    setResult(null);
    waitStartRef.current = new Date().toISOString();

    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    tickRef.current = setInterval(() => {
      setWaitElapsed((prev) => {
        if (prev + 1 >= timeout) {
          stopWaiting();
          setError('等待超时，未收到验证码');
          return prev + 1;
        }
        return prev + 1;
      });
    }, 1000);

    timerRef.current = setInterval(async () => {
      try {
        const r = await fetchLatest(true);
        if (r && waitStartRef.current) {
          const receivedAt = new Date(r.receivedDateTime).getTime();
          const startAt = new Date(waitStartRef.current).getTime();
          if (receivedAt > startAt - 5000 && r.extractedCode) {
            setResult(r);
            notifyUser(r.extractedCode);
            stopWaiting();
          }
        }
      } catch { /* keep polling */ }
    }, POLL_INTERVAL);
  }, [email, waiting, fetchLatest, notifyUser]);

  const stopWaiting = useCallback(() => {
    clearTimers();
    setWaiting(false);
    waitStartRef.current = null;
  }, [clearTimers]);

  return {
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
  };
}
