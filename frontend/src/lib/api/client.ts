import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import { API_PATHS, DEV_PUBLIC_TOKEN, RETRY_CONFIG } from '../constants';
import {
  setAuthTokens,
  clearAuthTokens,
  getStoredAccessToken,
  isAccessTokenValid,
  STORAGE_KEYS,
} from './auth';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  withCredentials: true,
  timeout: RETRY_CONFIG.REQUEST_TIMEOUT,
});

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  withCredentials: true,
});

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

  return DEV_PUBLIC_TOKEN;
}

interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

async function refreshToken(): Promise<string | null> {
  try {
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

export function isRequestCancelled(error: unknown): boolean {
  return axios.isCancel(error);
}

export function getApiClient() {
  return api;
}

export default api;
