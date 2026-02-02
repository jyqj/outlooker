import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useModalState } from '@/hooks/useModalState';

describe('useModalState', () => {
  it('should initialize with closed state', () => {
    const { result } = renderHook(() => useModalState());

    expect(result.current.isOpen).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('should open modal without data', () => {
    const { result } = renderHook(() => useModalState());

    act(() => {
      result.current.open();
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('should open modal with data', () => {
    const { result } = renderHook(() => useModalState<{ id: number }>());

    act(() => {
      result.current.open({ id: 123 });
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toEqual({ id: 123 });
  });

  it('should close modal and preserve data', () => {
    const { result } = renderHook(() => useModalState<string>());

    act(() => {
      result.current.open('test data');
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toBe('test data');

    act(() => {
      result.current.close();
    });

    expect(result.current.isOpen).toBe(false);
    expect(result.current.data).toBe('test data'); // close() preserves data
  });

  it('should set data independently', () => {
    const { result } = renderHook(() => useModalState<string>());

    act(() => {
      result.current.setData('new data');
    });

    expect(result.current.data).toBe('new data');
    expect(result.current.isOpen).toBe(false); // setData doesn't affect isOpen
  });
});
