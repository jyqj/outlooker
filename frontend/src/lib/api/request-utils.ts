import axios, { type AxiosError } from 'axios';
import { RETRY_CONFIG } from '../constants';

export interface CancellableRequest<T> {
  promise: Promise<T>;
  cancel: () => void;
}

export function createCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>
): CancellableRequest<T> {
  const controller = new AbortController();

  return {
    promise: requestFn(controller.signal),
    cancel: () => controller.abort(),
  };
}

class RequestDeduplicator {
  private pendingRequests = new Map<string, Promise<unknown>>();

  async dedupe<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending as Promise<T>;
    }

    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  clear(key: string): void {
    this.pendingRequests.delete(key);
  }

  clearAll(): void {
    this.pendingRequests.clear();
  }

  hasPending(key: string): boolean {
    return this.pendingRequests.has(key);
  }

  getPendingKeys(): string[] {
    return Array.from(this.pendingRequests.keys());
  }
}

export const requestDeduplicator = new RequestDeduplicator();

export interface RetryConfig {
  maxRetries?: number;
  retryDelay?: number;
  retryCondition?: (error: AxiosError) => boolean;
  exponentialBackoff?: boolean;
  onRetry?: (attempt: number, error: AxiosError) => void;
}

function isRetryableError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }

  if (axios.isCancel(error)) {
    return false;
  }

  if (!error.response) {
    return true;
  }

  const status = error.response.status;

  if (status >= 500) return true;
  if (status === 429) return true;
  if (status === 408) return true;

  return false;
}

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
      if (axios.isAxiosError(error)) {
        lastError = error;
      } else if (error instanceof Error) {
        lastError = error;
      } else {
        lastError = new Error(String(error));
      }

      const shouldRetry = retryCondition
        ? axios.isAxiosError(lastError) && retryCondition(lastError as AxiosError)
        : isRetryableError(lastError);

      if (!shouldRetry || attempt === maxRetries) {
        break;
      }

      if (onRetry && axios.isAxiosError(lastError)) {
        onRetry(attempt + 1, lastError as AxiosError);
      }

      const delay = exponentialBackoff
        ? retryDelay * Math.pow(2, attempt)
        : retryDelay;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  if (lastError) {
    throw lastError;
  }
  throw new Error('Retry loop completed unexpectedly');
}
