import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import type { BatchOperationResponse } from '@/types/api';
import { TIMING, API_PATHS, DEV_PUBLIC_TOKEN } from './constants';

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

  // 使用统一定义的开发环境默认值
  return DEV_PUBLIC_TOKEN;
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

// Tag statistics types
export interface TagStatItem {
  name: string;
  count: number;
  percentage: number;
}

export interface TagStats {
  total_accounts: number;
  tagged_accounts: number;
  untagged_accounts: number;
  tags: TagStatItem[];
}

export interface TagStatsResponse {
  success: boolean;
  data?: TagStats;
  message?: string;
}

// Pick account types
export interface PickAccountRequest {
  tag: string;
  exclude_tags?: string[];
  return_credentials?: boolean;
}

export interface PickAccountResult {
  email: string;
  tags: string[];
  password?: string;
  refresh_token?: string;
  client_id?: string;
}

export interface PickAccountResponse {
  success: boolean;
  data?: PickAccountResult;
  message?: string;
}

// Get tag statistics
export async function getTagStats(): Promise<TagStatsResponse> {
  const response = await api.get<TagStatsResponse>('/api/accounts/tags/stats');
  return response.data;
}

// Pick a random account and tag it
export async function pickAccount(request: PickAccountRequest): Promise<PickAccountResponse> {
  const response = await api.post<PickAccountResponse>('/api/accounts/pick', request);
  return response.data;
}

export default api;
