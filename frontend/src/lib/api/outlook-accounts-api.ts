import type { ApiResponse } from '@/types';
import api from './client';

export interface OutlookAccountCapabilities {
  email: string;
  imap_ready: boolean;
  graph_ready: boolean;
  protocol_ready: boolean;
  browser_fallback_ready: boolean;
  updated_at?: string;
}

export interface OutlookTokenRecord {
  id: number;
  oauth_config_id: number;
  email: string;
  access_token?: string;
  refresh_token?: string;
  expires_at?: string | null;
  scopes_granted?: string;
  status: string;
  last_error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface OutlookAccountView {
  email: string;
  status: string;
  account_type: string;
  source_account_email?: string | null;
  default_channel_id?: number | null;
  notes?: string;
  last_synced_at?: string | null;
  created_at?: string;
  updated_at?: string;
  token?: OutlookTokenRecord | null;
  capabilities?: OutlookAccountCapabilities | null;
}

export interface OutlookAccountDetail extends OutlookAccountView {
  profile_cache?: {
    email: string;
    profile_json: string;
    synced_at?: string;
    updated_at?: string;
  } | null;
  security_methods_snapshot?: Array<Record<string, unknown>>;
  recent_operations?: Array<Record<string, unknown>>;
}

export interface OutlookAccountsListData {
  items: OutlookAccountView[];
  total: number;
}

export interface BatchRefreshSummary {
  requested: number;
  refreshed: number;
  failed: number;
  details: Array<Record<string, unknown>>;
}

export interface OutlookAccountsParams {
  status?: string;
  account_type?: string;
  limit?: number;
  offset?: number;
}

export async function listOutlookAccounts(
  params: OutlookAccountsParams = {}
): Promise<ApiResponse<OutlookAccountsListData>> {
  const res = await api.get<ApiResponse<OutlookAccountsListData>>('/api/outlook/accounts', { params });
  return res.data;
}

export async function getOutlookAccountDetail(
  email: string
): Promise<ApiResponse<OutlookAccountDetail>> {
  const res = await api.get<ApiResponse<OutlookAccountDetail>>(`/api/outlook/accounts/${encodeURIComponent(email)}`);
  return res.data;
}

export async function refreshOutlookToken(
  email: string
): Promise<ApiResponse<OutlookTokenRecord>> {
  const res = await api.post<ApiResponse<OutlookTokenRecord>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/refresh-token`
  );
  return res.data;
}

export async function batchRefreshOutlookTokens(
  payload: { emails?: string[]; limit?: number; offset?: number; concurrency?: number } = {}
): Promise<ApiResponse<BatchRefreshSummary>> {
  const res = await api.post<ApiResponse<BatchRefreshSummary>>('/api/outlook/accounts/batch-refresh', payload);
  return res.data;
}

export async function getOutlookProfile(
  email: string,
  refresh = false
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.get<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/profile`,
    { params: refresh ? { refresh: true } : undefined }
  );
  return res.data;
}

export async function updateOutlookProfile(
  email: string,
  updates: Record<string, unknown>
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.patch<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/profile`,
    { updates }
  );
  return res.data;
}

export async function getOutlookAuthMethods(
  email: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.get<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/auth-methods`
  );
  return res.data;
}

export async function changeOutlookPassword(
  email: string,
  currentPassword: string,
  newPassword: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.post<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/change-password`,
    { current_password: currentPassword, new_password: newPassword }
  );
  return res.data;
}

export async function revokeOutlookSessions(
  email: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.post<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/revoke-sessions`
  );
  return res.data;
}

export async function getOutlookRiskyUsers(
  email: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.get<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/risky-users`
  );
  return res.data;
}

export async function dismissOutlookRisk(
  email: string,
  userId: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.post<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/dismiss-risk`,
    { user_id: userId }
  );
  return res.data;
}

export async function getOutlookMailboxSettings(
  email: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.get<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/mailbox-settings`
  );
  return res.data;
}

export async function updateOutlookMailboxSettings(
  email: string,
  updates: Record<string, unknown>
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.patch<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/mailbox-settings`,
    { updates }
  );
  return res.data;
}

export async function getOutlookRegionalSettings(
  email: string
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.get<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/regional-settings`
  );
  return res.data;
}

export async function updateOutlookRegionalSettings(
  email: string,
  updates: Record<string, unknown>
): Promise<ApiResponse<Record<string, unknown>>> {
  const res = await api.patch<ApiResponse<Record<string, unknown>>>(
    `/api/outlook/accounts/${encodeURIComponent(email)}/regional-settings`,
    { updates }
  );
  return res.data;
}
