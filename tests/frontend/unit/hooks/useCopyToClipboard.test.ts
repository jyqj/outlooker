import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';

describe('useCopyToClipboard', () => {
  const originalClipboard = navigator.clipboard;

  beforeEach(() => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    Object.assign(navigator, { clipboard: originalClipboard });
    vi.clearAllMocks();
  });

  it('should copy text to clipboard', async () => {
    const { result } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copy('test text');
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text');
  });

  it('should set copied state after copying', async () => {
    const { result } = renderHook(() => useCopyToClipboard(100));

    expect(result.current.copied).toBe(false);

    await act(async () => {
      await result.current.copy('test');
    });

    expect(result.current.copied).toBe(true);
  });

  it('should reset copied state after timeout', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useCopyToClipboard(100));

    await act(async () => {
      await result.current.copy('test');
    });

    expect(result.current.copied).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(150);
    });

    expect(result.current.copied).toBe(false);
    vi.useRealTimers();
  });

  it('should handle copy failure gracefully', async () => {
    (navigator.clipboard.writeText as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Copy failed')
    );

    const { result } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copy('test');
    });

    // Should not throw, copied should remain false
    expect(result.current.copied).toBe(false);
  });
});
