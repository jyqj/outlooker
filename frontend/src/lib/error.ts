/**
 * 统一错误处理工具模块
 * 提供标准化的错误处理和消息提取功能
 */

import { logError } from './utils';
import { MESSAGES } from './constants';

/**
 * API 错误响应类型
 */
export interface ApiError {
  response?: {
    data?: {
      message?: string;
      error_code?: string;
      details?: unknown;
    };
    status?: number;
  };
  message?: string;
}

/**
 * 从错误对象中提取用户友好的错误消息
 * @param error - 错误对象（通常是 axios 错误）
 * @param defaultMsg - 默认错误消息
 * @returns 用户友好的错误消息
 */
export function getErrorMessage(error: unknown, defaultMsg?: string): string {
  if (!error) {
    return defaultMsg || MESSAGES.GENERIC_ERROR;
  }

  // 处理 axios 错误响应
  const apiError = error as ApiError;
  if (apiError.response?.data?.message) {
    return apiError.response.data.message;
  }

  // 处理标准 Error 对象
  if (error instanceof Error && error.message) {
    return error.message;
  }

  // 处理字符串错误
  if (typeof error === 'string') {
    return error;
  }

  return defaultMsg || MESSAGES.GENERIC_ERROR;
}

/**
 * 获取 API 错误码
 * @param error - 错误对象
 * @returns 错误码或 undefined
 */
export function getErrorCode(error: unknown): string | undefined {
  const apiError = error as ApiError;
  return apiError.response?.data?.error_code;
}

/**
 * 获取 HTTP 状态码
 * @param error - 错误对象
 * @returns HTTP 状态码或 undefined
 */
export function getHttpStatus(error: unknown): number | undefined {
  const apiError = error as ApiError;
  return apiError.response?.status;
}

/**
 * 统一处理 API 错误
 * 记录日志并返回用户友好的错误消息
 * @param error - 错误对象
 * @param context - 错误上下文（用于日志）
 * @param defaultMsg - 默认错误消息
 * @returns 用户友好的错误消息
 */
export function handleApiError(
  error: unknown, 
  context: string, 
  defaultMsg?: string
): string {
  logError(context, error);
  return getErrorMessage(error, defaultMsg);
}

/**
 * 检查错误是否为认证错误（401）
 * @param error - 错误对象
 * @returns 是否为认证错误
 */
export function isAuthError(error: unknown): boolean {
  return getHttpStatus(error) === 401;
}

/**
 * 检查错误是否为权限错误（403）
 * @param error - 错误对象
 * @returns 是否为权限错误
 */
export function isForbiddenError(error: unknown): boolean {
  return getHttpStatus(error) === 403;
}

/**
 * 检查错误是否为资源不存在错误（404）
 * @param error - 错误对象
 * @returns 是否为资源不存在错误
 */
export function isNotFoundError(error: unknown): boolean {
  return getHttpStatus(error) === 404;
}

/**
 * 检查错误是否为速率限制错误（429）
 * @param error - 错误对象
 * @returns 是否为速率限制错误
 */
export function isRateLimitError(error: unknown): boolean {
  return getHttpStatus(error) === 429;
}

/**
 * 检查错误是否为服务器错误（5xx）
 * @param error - 错误对象
 * @returns 是否为服务器错误
 */
export function isServerError(error: unknown): boolean {
  const status = getHttpStatus(error);
  return status !== undefined && status >= 500 && status < 600;
}
