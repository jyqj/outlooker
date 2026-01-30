import { useCallback, useMemo, useState, useEffect } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import api from './api';
import { CONFIG } from './constants';
import { showError, showSuccess } from './toast';
import { logError } from './utils';
import type { ApiResponse, PaginatedData, Account, SystemConfig, SystemMetrics, Email } from '@/types';
import { getErrorMessage } from './error';
import { queryKeys } from './queryKeys';
import type { TagsData } from '@/types/api';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function useAsyncTask(initialLoading = false): {
  loading: boolean;
  run: <T>(task: () => Promise<T>) => Promise<T>;
  setLoading: (value: boolean) => void;
} {
  const [loading, setLoading] = useState(initialLoading);

  const run = useCallback(
    async <T,>(task: () => Promise<T>) => {
      setLoading(true);
      try {
        return await task();
      } finally {
        setLoading(false);
      }
    },
    [setLoading]
  );

  return { loading, run, setLoading };
}

export interface AccountsQueryParams {
  page?: number;
  search?: string;
  pageSize?: number;
}

export function useAccountsQuery({
  page,
  search,
  pageSize = CONFIG.DEFAULT_PAGE_SIZE,
}: AccountsQueryParams = {}): UseQueryResult<ApiResponse<PaginatedData<Account>>> {
  return useQuery({
    queryKey: queryKeys.accounts(page, search, pageSize),
    queryFn: async ({ signal }) => {
      const res = await api.get<ApiResponse<PaginatedData<Account>>>('/api/accounts/paged', {
        params: { page, page_size: pageSize, q: search },
        signal,
      });
      return res.data;
    },
    placeholderData: (previousData) => previousData,
  });
}

export function useAccountTagsQuery(): UseQueryResult<ApiResponse<TagsData>> {
  return useQuery({
    queryKey: queryKeys.tags(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<TagsData>>('/api/accounts/tags');
      return res.data;
    },
  });
}

export function useSystemConfigQuery(): UseQueryResult<ApiResponse<SystemConfig>> {
  return useQuery({
    queryKey: queryKeys.systemConfig(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<SystemConfig>>('/api/system/config');
      return res.data;
    },
  });
}

export function useSystemMetricsQuery(): UseQueryResult<ApiResponse<SystemMetrics>> {
  return useQuery({
    queryKey: queryKeys.systemMetrics(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<SystemMetrics>>('/api/system/metrics');
      return res.data;
    },
  });
}

export interface ApiActionOptions<T = unknown> {
  showSuccessToast?: boolean;
  showErrorToast?: boolean;
  successMessage?: string;
  errorMessage?: string;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
}

export interface ApiActionResult<T = unknown> {
  ok: boolean;
  data?: T;
  response?: unknown;
  error?: unknown;
}

export function useApiAction<T = unknown>(
  defaultOptions: ApiActionOptions<T> = {}
): (
  requestFn: () => Promise<{ data: ApiResponse<T> }>,
  overrideOptions?: ApiActionOptions<T>
) => Promise<ApiActionResult<T>> {
  const baseOptions = useMemo(
    () => ({
      showSuccessToast: true,
      showErrorToast: true,
      ...defaultOptions,
    }),
    [defaultOptions]
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
          return { ok: false, data: payload?.data, response };
        }

        const successMessage = options.successMessage ?? payload?.message;
        if (successMessage && options.showSuccessToast) {
          showSuccess(successMessage);
        }

        options.onSuccess?.(payload?.data as T);
        return { ok: true, data: payload?.data, response };
      } catch (error: unknown) {
        const message = getErrorMessage(error, options.errorMessage);
        logError(message, error);
        if (options.showErrorToast) {
          showError(message);
        }
        options.onError?.(error);
        return { ok: false, error };
      }
    },
    [baseOptions]
  );
}

export function useEmailMessagesQuery(
  email: string,
  options: {
    page?: number;
    pageSize?: number;
    refresh?: boolean;
    enabled?: boolean;
    refreshCounter?: number;
  } = {}
): UseQueryResult<ApiResponse<Email[] | { items: Email[] }>> {
  const { page = 1, pageSize = 1, refresh = false, enabled = true, refreshCounter = 0 } = options;

  return useQuery({
    queryKey: queryKeys.emailMessages(email, refreshCounter, page, pageSize),
    queryFn: async () => {
      const params: Record<string, unknown> = { email, page, page_size: pageSize };
      if (refresh || refreshCounter > 0) {
        params.refresh = true;
      }
      const res = await api.get<ApiResponse<Email[] | { items: Email[] }>>('/api/messages', {
        params,
      });
      return res.data;
    },
    enabled: enabled && !!email,
  });
}
