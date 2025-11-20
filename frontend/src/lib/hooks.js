import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from './api';
import { CONFIG } from './constants';
import { showError, showSuccess } from './toast';
import { logError } from './utils';

export function useAccountsQuery({
  page,
  search,
  pageSize = CONFIG.DEFAULT_PAGE_SIZE,
} = {}) {
  return useQuery({
    queryKey: ['accounts', page, search, pageSize],
    queryFn: async () => {
      const res = await api.get('/api/accounts/paged', {
        params: { page, page_size: pageSize, q: search },
      });
      return res.data;
    },
    keepPreviousData: true,
  });
}

export function useAccountTagsQuery() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      const res = await api.get('/api/accounts/tags');
      return res.data;
    },
  });
}

export function useSystemConfigQuery() {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: async () => {
      const res = await api.get('/api/system/config');
      return res.data;
    },
  });
}

export function useSystemMetricsQuery() {
  return useQuery({
    queryKey: ['system-metrics'],
    queryFn: async () => {
      const res = await api.get('/api/system/metrics');
      return res.data;
    },
  });
}

export function useApiAction(defaultOptions = {}) {
  const baseOptions = useMemo(
    () => ({
      showSuccessToast: true,
      showErrorToast: true,
      ...defaultOptions,
    }),
    [defaultOptions],
  );

  return useCallback(
    async (requestFn, overrideOptions = {}) => {
      const options = { ...baseOptions, ...overrideOptions };
      try {
        const response = await requestFn();
        const payload = response?.data;
        const businessSuccess = payload?.success !== false;

        if (!businessSuccess) {
          const message =
            payload?.message || options.errorMessage || '请求失败，请稍后重试';
          logError(message, payload);
          if (options.showErrorToast) {
            showError(message);
          }
          options.onError?.(payload);
          return { ok: false, data: payload, response };
        }

        const successMessage = options.successMessage ?? payload?.message;
        if (successMessage && options.showSuccessToast) {
          showSuccess(successMessage);
        }

        options.onSuccess?.(payload);
        return { ok: true, data: payload, response };
      } catch (error) {
        const message =
          error?.response?.data?.message ||
          options.errorMessage ||
          '请求失败，请稍后重试';
        logError(message, error);
        if (options.showErrorToast) {
          showError(message);
        }
        options.onError?.(error);
        return { ok: false, error, data: error?.response?.data };
      }
    },
    [baseOptions],
  );
}
