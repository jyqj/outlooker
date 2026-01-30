import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import type { BatchOperationResponse } from '@/types/api';
import { TIMING, API_PATHS } from './constants';

// 根据环境变量可自定义 API 地址，默认相对路径
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  withCredentials: true,
});

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  withCredentials: true,
});

const STORAGE_KEYS = {
  access: 'admin_token',
  accessExp: 'admin_token_expires_at',
  publicToken: 'public_api_token',
} as const;

let refreshPromise: Promise<string | null> | null = null;

function isPublicApiRequest(config: AxiosRequestConfig | InternalAxiosRequestConfig): boolean {
  const url = config?.url || '';
  return API_PATHS.PUBLIC.some(prefix => url.startsWith(prefix) || url.includes(`${prefix}/`));
}

function isAdminProtectedRequest(config: AxiosRequestConfig | InternalAxiosRequestConfig): boolean {
  const url = config?.url || '';
  return API_PATHS.ADMIN.some(prefix => url.startsWith(prefix));
}

function getPublicApiToken(): string | null {
  const envToken = import.meta.env.VITE_PUBLIC_API_TOKEN as string | undefined;
  if (envToken) return envToken;

  const stored = sessionStorage.getItem(STORAGE_KEYS.publicToken);
  if (stored) return stored;

  // 与后端 settings 的开发环境 fallback 对齐
  // 在没有配置 VITE_PUBLIC_API_TOKEN 时使用默认值
  // 直接硬编码以确保在生产构建中可用
  return 'dev-public-token-change-me';
}

export interface AuthTokensInput {
  accessToken: string;
  expiresIn: number;
}

export function setAuthTokens({ accessToken, expiresIn }: AuthTokensInput): void {
  const now = Date.now();
  if (accessToken && expiresIn) {
    sessionStorage.setItem(STORAGE_KEYS.access, accessToken);
    sessionStorage.setItem(STORAGE_KEYS.accessExp, String(now + expiresIn * 1000));
  }
}

export function clearAuthTokens(): void {
  sessionStorage.removeItem(STORAGE_KEYS.access);
  sessionStorage.removeItem(STORAGE_KEYS.accessExp);
}

function getStoredAccessToken(): string | null {
  return sessionStorage.getItem(STORAGE_KEYS.access);
}

function isAccessTokenValid(): boolean {
  const expiresAt = Number(sessionStorage.getItem(STORAGE_KEYS.accessExp) || 0);
  if (!expiresAt) return false;
  return expiresAt - Date.now() > TIMING.TOKEN_CLOCK_SKEW;
}

interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

async function refreshToken(): Promise<string | null> {
  try {
    // 仅依赖后端 HttpOnly Cookie 的 refresh token
    const res = await refreshClient.post<RefreshResponse>('/api/admin/refresh', {});
    const data = res.data;
    setAuthTokens({
      accessToken: data.access_token,
      expiresIn: data.expires_in,
    });
    return data.access_token;
  } catch {
    clearAuthTokens();
    return null;
  } finally {
    refreshPromise = null;
  }
}

async function ensureFreshAccessToken(): Promise<string | null> {
  const access = getStoredAccessToken();
  if (access && isAccessTokenValid()) {
    return access;
  }
  if (!refreshPromise) {
    refreshPromise = refreshToken();
  }
  return refreshPromise;
}

api.interceptors.request.use(async (config) => {
  if (isAdminProtectedRequest(config)) {
    const token = await ensureFreshAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  if (isPublicApiRequest(config)) {
    const token = getPublicApiToken();
    if (token) {
      config.headers['X-Public-Token'] = token;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (
      error.response &&
      error.response.status === 401 &&
      isAdminProtectedRequest(error.config)
    ) {
      clearAuthTokens();
      if (!window.location.pathname.startsWith('/admin/login')) {
        window.location.href = '/admin/login';
      }
    }
    return Promise.reject(error);
  }
);

// Batch operations - types imported from @/types/api
export { type BatchOperationResponse } from '@/types/api';

export async function batchDeleteAccounts(emails: string[]): Promise<BatchOperationResponse> {
  const response = await api.post<BatchOperationResponse>('/api/accounts/batch-delete', { emails });
  return response.data;
}

export async function batchUpdateTags(
  emails: string[],
  tags: string[],
  mode: 'add' | 'remove' | 'set'
): Promise<BatchOperationResponse> {
  const response = await api.post<BatchOperationResponse>('/api/accounts/batch-tags', {
    emails,
    tags,
    mode,
  });
  return response.data;
}

export default api;
