export { default } from './client';

export { STORAGE_KEYS, setAuthTokens, clearAuthTokens, getStoredAccessToken, isAccessTokenValid } from './auth';
export type { AuthTokensInput } from './auth';

export { isRequestCancelled, getApiClient } from './client';

export { requestDeduplicator, createCancellableRequest, withRetry } from './request-utils';
export type { CancellableRequest, RetryConfig } from './request-utils';

export {
  batchDeleteAccounts,
  batchUpdateTags,
  pickAccount,
  getAccounts,
  getAccountsCancellable,
  clearAccountsCache,
  getAccountsPaged,
} from './accounts-api';
export type { AccountsResponse, PagedAccountsParams } from './accounts-api';

export {
  getTagStats,
  getTagStatsCancellable,
  getAllTags,
  getAllTagsCancellable,
  deleteTagGlobally,
  renameTagGlobally,
} from './tags-api';

export {
  getDashboardSummary,
  runHealthCheck,
} from './dashboard-api';

// Backward-compatible type re-exports (consumers may import these from @/lib/api)
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
  BatchOperationResponse,
} from '@/types/api';
