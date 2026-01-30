/**
 * API response type definitions
 */

import type { Account, Email, SystemConfig, SystemMetrics, ImportResult, PaginatedData } from './models';

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  data?: T;
}

/**
 * Error response from API
 */
export interface ApiError {
  success: false;
  message: string;
  error_code?: string;
  details?: Record<string, unknown>;
}

/**
 * Account list response
 */
export type AccountsResponse = ApiResponse<Account[]>;

/**
 * Paginated accounts response
 */
export type PaginatedAccountsResponse = ApiResponse<PaginatedData<Account>>;

/**
 * Single account response
 */
export type AccountResponse = ApiResponse<Account>;

/**
 * Email messages response
 */
export type MessagesResponse = ApiResponse<Email[]>;

/**
 * System config response
 */
export type SystemConfigResponse = ApiResponse<SystemConfig>;

/**
 * System metrics response
 */
export type SystemMetricsResponse = ApiResponse<SystemMetrics>;

/**
 * Import response
 */
export type ImportResponse = ApiResponse<ImportResult>;

/**
 * Tags list with accounts mapping
 */
export interface TagsData {
  tags: string[];
  accounts: Record<string, string[]>;
}

/**
 * Tags response
 */
export type TagsResponse = ApiResponse<TagsData>;

/**
 * Type guard to check if data is TagsData
 */
export function isTagsData(data: unknown): data is TagsData {
  return (
    typeof data === 'object' &&
    data !== null &&
    'tags' in data &&
    'accounts' in data &&
    Array.isArray((data as TagsData).tags) &&
    typeof (data as TagsData).accounts === 'object'
  );
}

/**
 * Auth login response
 */
export interface LoginResponse {
  success: boolean;
  message?: string;
  access_token?: string;
  token_type?: string;
}

/**
 * Auth refresh response
 */
export interface RefreshResponse {
  success: boolean;
  access_token?: string;
  token_type?: string;
}

/**
 * Public account response (for verification page)
 */
export interface PublicAccountResponse {
  success: boolean;
  message?: string;
  email?: string;
}

/**
 * OTP response
 */
export interface OTPResponse {
  success: boolean;
  message?: string;
  otp?: string;
  source?: string;
}

/**
 * API request configuration
 */
export interface RequestConfig {
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean>;
  timeout?: number;
}

/**
 * Messages request parameters
 */
export interface MessagesParams {
  email: string;
  top?: number;
  folder?: string;
  refresh?: boolean;
}

/**
 * Batch delete request
 */
export interface BatchDeleteRequest {
  emails: string[];
}

/**
 * Batch tags update request
 */
export interface BatchTagsRequest {
  emails: string[];
  tags: string[];
  mode: 'set' | 'add' | 'remove';
}

/**
 * Batch operation response (unified for delete and tags)
 */
export interface BatchOperationResponse {
  success: boolean;
  message: string;
  data?: {
    deleted_count?: number;
    updated_count?: number;
    failed_count?: number;
    requested_count: number;
    tags?: string[];
    mode?: string;
  };
}
