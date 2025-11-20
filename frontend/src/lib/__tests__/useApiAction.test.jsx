import { renderHook, act } from '@testing-library/react';
import { useApiAction } from '../hooks';
import { showError, showSuccess } from '../toast';
import { logError } from '../utils';

vi.mock('../toast', () => ({
  showSuccess: vi.fn(),
  showError: vi.fn(),
}));

vi.mock('../utils', async () => {
  const actual = await vi.importActual('../utils');
  return {
    ...actual,
    logError: vi.fn(),
  };
});

describe('useApiAction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows success toast when request succeeds', async () => {
    const { result } = renderHook(() => useApiAction());
    const requestFn = vi.fn().mockResolvedValue({
      data: { success: true, message: 'ok' },
    });

    await act(async () => {
      const response = await result.current(requestFn, {
        successMessage: '配置更新成功',
      });
      expect(response.ok).toBe(true);
    });

    expect(showSuccess).toHaveBeenCalledWith('配置更新成功');
    expect(showError).not.toHaveBeenCalled();
    expect(logError).not.toHaveBeenCalled();
  });

  it('logs and notifies when business request fails', async () => {
    const { result } = renderHook(() => useApiAction());
    const payload = { success: false, message: '业务失败' };
    const requestFn = vi.fn().mockResolvedValue({ data: payload });

    await act(async () => {
      const response = await result.current(requestFn, {
        errorMessage: '请求失败',
      });
      expect(response.ok).toBe(false);
    });

    expect(logError).toHaveBeenCalledWith('业务失败', payload);
    expect(showError).toHaveBeenCalledWith('业务失败');
    expect(showSuccess).not.toHaveBeenCalled();
  });

  it('handles network errors with log and fallback toast', async () => {
    const { result } = renderHook(() => useApiAction());
    const networkError = new Error('网络失败');
    networkError.response = { data: { message: '后端报错' } };
    const requestFn = vi.fn().mockRejectedValue(networkError);

    await act(async () => {
      const response = await result.current(requestFn, {
        errorMessage: '默认错误',
      });
      expect(response.ok).toBe(false);
    });

    expect(logError).toHaveBeenCalledWith('后端报错', networkError);
    expect(showError).toHaveBeenCalledWith('后端报错');
  });
});
