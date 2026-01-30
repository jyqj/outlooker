import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getErrorMessage,
  getErrorCode,
  getHttpStatus,
  handleApiError,
  isAuthError,
  isForbiddenError,
  isNotFoundError,
  isRateLimitError,
  isServerError,
} from '../error';

// Mock logError
vi.mock('../utils', () => ({
  logError: vi.fn(),
}));

describe('error utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getErrorMessage', () => {
    it('returns API error message when available', () => {
      const error = {
        response: {
          data: {
            message: 'API error message',
          },
        },
      };
      expect(getErrorMessage(error)).toBe('API error message');
    });

    it('returns default message when no API message', () => {
      const error = {};
      expect(getErrorMessage(error, 'Default message')).toBe('Default message');
    });

    it('returns generic error when no message available', () => {
      expect(getErrorMessage(null)).toBe('发生未知错误，请稍后重试');
    });

    it('handles Error objects', () => {
      const error = new Error('Error message');
      expect(getErrorMessage(error)).toBe('Error message');
    });

    it('handles string errors', () => {
      expect(getErrorMessage('String error')).toBe('String error');
    });
  });

  describe('getErrorCode', () => {
    it('returns error code when available', () => {
      const error = {
        response: {
          data: {
            error_code: 'AUTH_ERROR',
          },
        },
      };
      expect(getErrorCode(error)).toBe('AUTH_ERROR');
    });

    it('returns undefined when no error code', () => {
      const error = {};
      expect(getErrorCode(error)).toBeUndefined();
    });
  });

  describe('getHttpStatus', () => {
    it('returns status when available', () => {
      const error = {
        response: {
          status: 401,
        },
      };
      expect(getHttpStatus(error)).toBe(401);
    });

    it('returns undefined when no status', () => {
      const error = {};
      expect(getHttpStatus(error)).toBeUndefined();
    });
  });

  describe('handleApiError', () => {
    it('logs error and returns message', () => {
      const error = {
        response: {
          data: {
            message: 'API error',
          },
        },
      };
      const result = handleApiError(error, 'Test context');
      expect(result).toBe('API error');
    });
  });

  describe('error type checks', () => {
    it('isAuthError returns true for 401', () => {
      const error = { response: { status: 401 } };
      expect(isAuthError(error)).toBe(true);
    });

    it('isForbiddenError returns true for 403', () => {
      const error = { response: { status: 403 } };
      expect(isForbiddenError(error)).toBe(true);
    });

    it('isNotFoundError returns true for 404', () => {
      const error = { response: { status: 404 } };
      expect(isNotFoundError(error)).toBe(true);
    });

    it('isRateLimitError returns true for 429', () => {
      const error = { response: { status: 429 } };
      expect(isRateLimitError(error)).toBe(true);
    });

    it('isServerError returns true for 5xx', () => {
      expect(isServerError({ response: { status: 500 } })).toBe(true);
      expect(isServerError({ response: { status: 502 } })).toBe(true);
      expect(isServerError({ response: { status: 503 } })).toBe(true);
      expect(isServerError({ response: { status: 400 } })).toBe(false);
    });
  });
});
