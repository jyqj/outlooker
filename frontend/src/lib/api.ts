import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig, type AxiosError } from 'axios';
import type {
  BatchOperationResponse,
  TagStatsResponse,
  PickAccountRequest,
  PickAccountResponse,
  TagListResponse,
  TagOperationResponse,
  AccountsParams,
  AccountsListResponse,
} from '@/types/api';
import type { ApiResponse, PaginatedData, Account } from '@/types';
import { TIMING, API_PATHS, DEV_PUBLIC_TOKEN, RETRY_CONFIG } from './constants';

// Re-export types for backwards compatibility (files may import these from @/lib/api)
export type {
  TagStatItem,
  TagStats,
  TagStatsResponse,
  PickAccountRequest,
  PickAccountResult,
  PickAccountResponse,
  TagListResponse,
  TagOperationResponse,
  AccountsParams,
  AccountsListResponse,
} from '@/types/api';

// Type alias for backwards compatibility
export type AccountsResponse = AccountsListResponse;

// ============================================================================
// 请求取消支持
// ============================================================================

/**
 * 可取消请求接口
 */
export interface CancellableRequest<T> {
  promise: Promise<T>;
  cancel: () => void;
}

/**
 * 创建可取消的请求
 * @param requestFn 接受 AbortSignal 的请求函数
 * @returns 包含 promise 和 cancel 方法的对象
 */
export function createCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>
): CancellableRequest<T> {
  const controller = new AbortController();

  return {
    promise: requestFn(controller.signal),
    cancel: () => controller.abort(),
  };
}

// ============================================================================
// 请求去重管理
// ============================================================================

/**
 * 请求去重管理器
 * 防止相同请求同时发起多次
 */
class RequestDeduplicator {
  private pendingRequests = new Map<string, Promise<unknown>>();

  /**
   * 去重执行请求
   * @param key 请求唯一标识
   * @param requestFn 请求函数
   * @returns 请求结果
   */
  async dedupe<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    // 如果已有相同请求在进行中，返回该请求的 Promise
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending as Promise<T>;
    }

    // 创建新请求
    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  /**
   * 清除指定请求
   */
  clear(key: string): void {
    this.pendingRequests.delete(key);
  }

  /**
   * 清除所有请求
   */
  clearAll(): void {
    this.pendingRequests.clear();
  }

  /**
   * 检查是否有指定请求在进行中
   */
  hasPending(key: string): boolean {
    return this.pendingRequests.has(key);
  }

  /**
   * 获取所有进行中的请求 key
   */
  getPendingKeys(): string[] {
    return Array.from(this.pendingRequests.keys());
  }
}

export const requestDeduplicator = new RequestDeduplicator();

// ============================================================================
// 请求重试机制
// ============================================================================

/**
 * 重试配置接口
 */
export interface RetryConfig {
  /** 最大重试次数，默认 3 */
  maxRetries?: number;
  /** 基础重试延迟（毫秒），默认 1000 */
  retryDelay?: number;
  /** 自定义重试条件判断函数 */
  retryCondition?: (error: AxiosError) => boolean;
  /** 是否使用指数退避，默认 true */
  exponentialBackoff?: boolean;
  /** 重试时的回调函数 */
  onRetry?: (attempt: number, error: AxiosError) => void;
}

/**
 * 判断是否为可重试的错误
 * - 网络错误（无响应）
 * - 5xx 服务器错误
 * - 429 请求过多
 * - 请求超时
 */
function isRetryableError(error: unknown): boolean {
  // 非 AxiosError 不重试
  if (!axios.isAxiosError(error)) {
    return false;
  }

  // 请求被取消不重试
  if (axios.isCancel(error)) {
    return false;
  }

  // 网络错误（无响应）可重试
  if (!error.response) {
    return true;
  }

  const status = error.response.status;

  // 5xx 服务器错误可重试
  if (status >= 500) {
    return true;
  }

  // 429 请求过多可重试
  if (status === 429) {
    return true;
  }

  // 408 请求超时可重试
  if (status === 408) {
    return true;
  }

  return false;
}

/**
 * 带重试功能的请求包装器
 * @param requestFn 请求函数
 * @param config 重试配置
 * @returns 请求结果
 */
export async function withRetry<T>(
  requestFn: () => Promise<T>,
  config: RetryConfig = {}
): Promise<T> {
  const {
    maxRetries = RETRY_CONFIG.MAX_RETRIES,
    retryDelay = RETRY_CONFIG.RETRY_DELAY,
    retryCondition,
    exponentialBackoff = true,
    onRetry,
  } = config;

  let lastError: AxiosError | Error | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      // 使用 axios 的类型守卫
      if (axios.isAxiosError(error)) {
        lastError = error;
      } else if (error instanceof Error) {
        lastError = error;
      } else {
        lastError = new Error(String(error));
      }

      // 检查是否应该重试
      const shouldRetry = retryCondition
        ? axios.isAxiosError(lastError) && retryCondition(lastError as AxiosError)
        : isRetryableError(lastError);

      if (!shouldRetry || attempt === maxRetries) {
        break;
      }

      // 回调通知
      if (onRetry && axios.isAxiosError(lastError)) {
        onRetry(attempt + 1, lastError as AxiosError);
      }

      // 等待后重试
      const delay = exponentialBackoff
        ? retryDelay * Math.pow(2, attempt)
        : retryDelay;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  // 确保有错误可抛出
  if (lastError) {
    throw lastError;
  }
  throw new Error('Retry loop completed unexpectedly');
}

// ============================================================================
// Axios 实例配置
// ============================================================================

// 根据环境变量可自定义 API 地址，默认相对路径
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  withCredentials: true,
  timeout: RETRY_CONFIG.REQUEST_TIMEOUT,
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

export function getStoredAccessToken(): string | null {
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

// ============================================================================
// 批量操作 API
// ============================================================================

// Batch operations - types imported from @/types/api
export { type BatchOperationResponse } from '@/types/api';

export async function batchDeleteAccounts(
  emails: string[],
  options: { retry?: boolean } = {}
): Promise<BatchOperationResponse> {
  const { retry = false } = options;

  const requestFn = () =>
    api.post<BatchOperationResponse>('/api/accounts/batch-delete', { emails })
      .then(res => res.data);

  return retry ? withRetry(requestFn) : requestFn();
}

export async function batchUpdateTags(
  emails: string[],
  tags: string[],
  mode: 'add' | 'remove' | 'set',
  options: { retry?: boolean } = {}
): Promise<BatchOperationResponse> {
  const { retry = false } = options;

  const requestFn = () =>
    api.post<BatchOperationResponse>('/api/accounts/batch-tags', {
      emails,
      tags,
      mode,
    }).then(res => res.data);

  return retry ? withRetry(requestFn) : requestFn();
}


// ============================================================================
// 标签统计 API
// ============================================================================

/**
 * 获取标签统计（带去重）
 */
export async function getTagStats(options: { dedupe?: boolean; retry?: boolean } = {}): Promise<TagStatsResponse> {
  const { dedupe = true, retry = true } = options;

  const requestFn = () =>
    api.get<TagStatsResponse>('/api/accounts/tags/stats').then(res => res.data);

  const retryFn = () => (retry ? withRetry(requestFn) : requestFn());

  if (dedupe) {
    return requestDeduplicator.dedupe('tag-stats', retryFn);
  }

  return retryFn();
}

/**
 * 获取标签统计（可取消版本）
 */
export function getTagStatsCancellable(): CancellableRequest<TagStatsResponse> {
  return createCancellableRequest((signal) =>
    api.get<TagStatsResponse>('/api/accounts/tags/stats', { signal }).then(res => res.data)
  );
}

// ============================================================================
// 账户选取 API
// ============================================================================

/**
 * 选取随机账户并标记
 */
export async function pickAccount(
  request: PickAccountRequest,
  options: { retry?: boolean } = {}
): Promise<PickAccountResponse> {
  const { retry = true } = options;

  const requestFn = () =>
    api.post<PickAccountResponse>('/api/accounts/pick', request).then(res => res.data);

  return retry ? withRetry(requestFn) : requestFn();
}

// ============================================================================
// 标签管理 API
// ============================================================================


/**
 * 获取所有标签列表（带去重和重试）
 */
export async function getAllTags(options: { dedupe?: boolean; retry?: boolean } = {}): Promise<TagListResponse> {
  const { dedupe = true, retry = true } = options;

  const requestFn = () =>
    api.get<TagListResponse>('/api/tags').then(res => res.data);

  const retryFn = () => (retry ? withRetry(requestFn) : requestFn());

  if (dedupe) {
    return requestDeduplicator.dedupe('all-tags', retryFn);
  }

  return retryFn();
}

/**
 * 获取所有标签列表（可取消版本）
 */
export function getAllTagsCancellable(): CancellableRequest<TagListResponse> {
  return createCancellableRequest((signal) =>
    api.get<TagListResponse>('/api/tags', { signal }).then(res => res.data)
  );
}

/**
 * 全局删除标签
 */
export async function deleteTagGlobally(
  tagName: string,
  options: { retry?: boolean } = {}
): Promise<TagOperationResponse> {
  const { retry = false } = options;

  const requestFn = () =>
    api.delete<TagOperationResponse>(`/api/tags/${encodeURIComponent(tagName)}`)
      .then(res => res.data);

  // 删除操作后清除相关缓存
  const result = retry ? await withRetry(requestFn) : await requestFn();

  // 清除标签相关的去重缓存
  requestDeduplicator.clear('all-tags');
  requestDeduplicator.clear('tag-stats');

  return result;
}

/**
 * 全局重命名标签
 */
export async function renameTagGlobally(
  oldName: string,
  newName: string,
  options: { retry?: boolean } = {}
): Promise<TagOperationResponse> {
  const { retry = false } = options;

  const requestFn = () =>
    api.put<TagOperationResponse>(
      `/api/tags/${encodeURIComponent(oldName)}`,
      { new_name: newName }
    ).then(res => res.data);

  const result = retry ? await withRetry(requestFn) : await requestFn();

  // 清除标签相关的去重缓存
  requestDeduplicator.clear('all-tags');
  requestDeduplicator.clear('tag-stats');

  return result;
}

// ============================================================================
// 通用账户列表 API（带完整优化支持）
// ============================================================================


/**
 * 生成账户请求的去重 key
 */
function getAccountsDedupeKey(params: AccountsParams): string {
  return `accounts:${JSON.stringify(params)}`;
}

/**
 * 获取账户列表（带去重和重试）
 */
export async function getAccounts(
  params: AccountsParams = {},
  options: { dedupe?: boolean; retry?: boolean } = {}
): Promise<AccountsResponse> {
  const { dedupe = true, retry = true } = options;

  const requestFn = () =>
    api.get<AccountsResponse>('/api/accounts', { params }).then(res => res.data);

  const retryFn = () => (retry ? withRetry(requestFn) : requestFn());

  if (dedupe) {
    return requestDeduplicator.dedupe(getAccountsDedupeKey(params), retryFn);
  }

  return retryFn();
}

/**
 * 获取账户列表（可取消版本）
 */
export function getAccountsCancellable(params: AccountsParams = {}): CancellableRequest<AccountsResponse> {
  return createCancellableRequest((signal) =>
    api.get<AccountsResponse>('/api/accounts', { params, signal }).then(res => res.data)
  );
}

/**
 * 清除账户列表的去重缓存
 */
export function clearAccountsCache(params?: AccountsParams): void {
  if (params) {
    requestDeduplicator.clear(getAccountsDedupeKey(params));
  } else {
    // 清除所有 accounts 相关的缓存
    const keys = requestDeduplicator.getPendingKeys();
    keys.forEach(key => {
      if (key.startsWith('accounts:')) {
        requestDeduplicator.clear(key);
      }
    });
  }
}

// ============================================================================
// 工具函数导出
// ============================================================================

/**
 * 检查错误是否为请求取消
 */
export function isRequestCancelled(error: unknown): boolean {
  return axios.isCancel(error);
}

/**
 * 获取 axios 实例（用于自定义请求）
 */
export function getApiClient() {
  return api;
}

// ============================================================================
// 分页账户列表 API
// ============================================================================

export interface PagedAccountsParams {
  page?: number;
  page_size?: number;
  q?: string;
}

export async function getAccountsPaged(
  params: PagedAccountsParams = {}
): Promise<ApiResponse<PaginatedData<Account>>> {
  const res = await api.get<ApiResponse<PaginatedData<Account>>>('/api/accounts/paged', { params });
  return res.data;
}

export default api;
