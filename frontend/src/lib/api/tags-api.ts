import type {
  TagStatsResponse,
  TagListResponse,
  TagOperationResponse,
} from '@/types/api';
import api from './client';
import { requestDeduplicator, withRetry, createCancellableRequest, type CancellableRequest } from './request-utils';

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

export function getTagStatsCancellable(): CancellableRequest<TagStatsResponse> {
  return createCancellableRequest((signal) =>
    api.get<TagStatsResponse>('/api/accounts/tags/stats', { signal }).then(res => res.data)
  );
}

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

export function getAllTagsCancellable(): CancellableRequest<TagListResponse> {
  return createCancellableRequest((signal) =>
    api.get<TagListResponse>('/api/tags', { signal }).then(res => res.data)
  );
}

export async function deleteTagGlobally(
  tagName: string,
  options: { retry?: boolean } = {}
): Promise<TagOperationResponse> {
  const { retry = false } = options;

  const requestFn = () =>
    api.delete<TagOperationResponse>(`/api/tags/${encodeURIComponent(tagName)}`)
      .then(res => res.data);

  const result = retry ? await withRetry(requestFn) : await requestFn();

  requestDeduplicator.clear('all-tags');
  requestDeduplicator.clear('tag-stats');

  return result;
}

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

  requestDeduplicator.clear('all-tags');
  requestDeduplicator.clear('tag-stats');

  return result;
}
