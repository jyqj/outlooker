/**
 * Data model type definitions
 */

/**
 * Email account information
 */
export interface Account {
  email: string;
  password?: string;
  client_id?: string;
  refresh_token?: string;
  is_used: boolean;
  last_used_at: string | null;
  tags?: string[];
}

/**
 * Email address details
 */
export interface EmailAddress {
  name: string;
  address: string;
}

/**
 * Email sender/recipient information
 */
export interface EmailParticipant {
  emailAddress: EmailAddress;
}

/**
 * Email body content
 */
export interface EmailBody {
  content: string;
  contentType: 'text' | 'html';
}

/**
 * Email message
 */
export interface Email {
  id: string;
  subject: string;
  receivedDateTime: string;
  sender?: EmailParticipant;
  from?: EmailParticipant;
  toRecipients?: EmailParticipant[];
  body?: EmailBody;
  bodyPreview?: string;
}

/**
 * Extracted OTP (One-Time Password) information
 */
export interface OTPInfo {
  code: string;
  source?: string;
  timestamp?: string;
}

/**
 * System configuration
 */
export interface SystemConfig {
  email_limit: number;
}

/**
 * System metrics
 */
export interface SystemMetrics {
  email_manager: {
    cache_hits: number;
    cache_misses: number;
    client_reuses: number;
    client_creates: number;
    db_loads: number;
    cache_refreshes: number;
    last_cache_refresh_at: string | null;
    accounts_source: string;
    accounts_count: number;
    cache_hit_rate: number | null;
    email_cache: {
      total_messages: number;
      cached_accounts: number;
    };
  };
  database: Record<string, { value: string; updated_at: string }>;
  warning?: string;
}

/**
 * Account import entry
 */
export interface ImportEntry {
  email: string;
  password?: string;
  client_id?: string;
  refresh_token: string;
}

/**
 * Import result detail entry
 */
export interface ImportResultDetail {
  action?: string;
  email?: string;
  message?: string;
}

/**
 * Import result - matches backend ImportResult model
 */
export interface ImportResult {
  success: boolean;
  total_count: number;
  added_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  details: ImportResultDetail[];
  message?: string;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * JWT tokens
 */
export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

/**
 * Admin user information
 */
export interface AdminUser {
  id: number;
  username: string;
  role: string;
  is_active?: boolean;
}

/**
 * Admin login response from backend
 */
export interface AdminLoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  user: AdminUser;
}

/**
 * Pagination information
 */
export interface PaginationInfo {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedData<T> {
  items: T[];
  pagination?: PaginationInfo;
  total?: number;
  page?: number;
  page_size?: number;
}
