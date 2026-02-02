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

// ============================================================================
// Tag Statistics Types
// ============================================================================

/**
 * Single tag statistic item
 */
export interface TagStatItem {
  name: string;
  count: number;
  percentage: number;
}

/**
 * Tag statistics summary
 */
export interface TagStats {
  total_accounts: number;
  tagged_accounts: number;
  untagged_accounts: number;
  tags: TagStatItem[];
}

/**
 * Tag statistics API response
 */
export interface TagStatsResponse {
  success: boolean;
  data?: TagStats;
  message?: string;
}

// ============================================================================
// Pick Account Types
// ============================================================================

/**
 * Request parameters for picking a random account
 */
export interface PickAccountRequest {
  tag: string;
  exclude_tags?: string[];
  return_credentials?: boolean;
}

/**
 * Result data from pick account operation
 */
export interface PickAccountResult {
  email: string;
  tags: string[];
  password?: string;
  refresh_token?: string;
  client_id?: string;
}

/**
 * Pick account API response
 */
export interface PickAccountResponse {
  success: boolean;
  data?: PickAccountResult;
  message?: string;
}

// ============================================================================
// Tag Management Types
// ============================================================================

/**
 * Tag list API response
 */
export interface TagListResponse {
  success: boolean;
  data?: { tags: string[] };
  message?: string;
}

/**
 * Tag operation (create/rename/delete) API response
 */
export interface TagOperationResponse {
  success: boolean;
  message?: string;
  data?: {
    tag?: string;
    old_name?: string;
    new_name?: string;
    affected_accounts?: number;
  };
}

// ============================================================================
// Account List Types
// ============================================================================

/**
 * Parameters for fetching accounts list
 */
export interface AccountsParams {
  page?: number;
  page_size?: number;
  search?: string;
  tag?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * Paginated accounts list API response
 */
export interface AccountsListResponse {
  success: boolean;
  data?: {
    accounts: Account[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  message?: string;
}
