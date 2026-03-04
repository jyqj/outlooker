import type {
  BatchOperationResponse,
  PickAccountRequest,
  PickAccountResponse,
  AccountsParams,
  AccountsListResponse,
} from '@/types/api';
import type { ApiResponse, PaginatedData, Account } from '@/types';
import api from './client';
import { requestDeduplicator, withRetry, createCancellableRequest, type CancellableRequest } from './request-utils';

export type AccountsResponse = AccountsListResponse;

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

export async function pickAccount(
  request: PickAccountRequest,
  options: { retry?: boolean } = {}
): Promise<PickAccountResponse> {
  const { retry = true } = options;

  const requestFn = () =>
    api.post<PickAccountResponse>('/api/accounts/pick', request).then(res => res.data);

  return retry ? withRetry(requestFn) : requestFn();
}

function getAccountsDedupeKey(params: AccountsParams): string {
  return `accounts:${JSON.stringify(params)}`;
}

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

export function getAccountsCancellable(params: AccountsParams = {}): CancellableRequest<AccountsResponse> {
  return createCancellableRequest((signal) =>
    api.get<AccountsResponse>('/api/accounts', { params, signal }).then(res => res.data)
  );
}

export function clearAccountsCache(params?: AccountsParams): void {
  if (params) {
    requestDeduplicator.clear(getAccountsDedupeKey(params));
  } else {
    const keys = requestDeduplicator.getPendingKeys();
    keys.forEach(key => {
      if (key.startsWith('accounts:')) {
        requestDeduplicator.clear(key);
      }
    });
  }
}

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
