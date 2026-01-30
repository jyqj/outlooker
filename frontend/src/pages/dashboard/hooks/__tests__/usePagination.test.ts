import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePagination } from '../usePagination';

describe('usePagination', () => {
  const onError = vi.fn();
  const defaultOptions = {
    initialPage: 1,
    initialPageSize: 10,
    totalRecords: 100,
    onError,
  };

  beforeEach(() => {
    onError.mockClear();
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(10);
    expect(result.current.totalPages).toBe(10);
    expect(result.current.isFirstPage).toBe(true);
    expect(result.current.isLastPage).toBe(false);
  });

  it('calculates totalPages correctly', () => {
    const { result } = renderHook(() => usePagination({ 
      ...defaultOptions, 
      totalRecords: 55, 
      initialPageSize: 10 
    }));
    
    expect(result.current.totalPages).toBe(6);
  });

  it('handles page size change', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.handlePageSizeChange('20');
    });
    
    expect(result.current.pageSize).toBe(20);
    expect(result.current.page).toBe(1); // Resets to page 1
    expect(result.current.totalPages).toBe(5);
  });

  it('goes to next page', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.nextPage();
    });
    
    expect(result.current.page).toBe(2);
    expect(result.current.isFirstPage).toBe(false);
  });

  it('goes to previous page', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, initialPage: 3 }));
    
    act(() => {
      result.current.prevPage();
    });
    
    expect(result.current.page).toBe(2);
  });

  it('does not go below page 1', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.prevPage();
    });
    
    expect(result.current.page).toBe(1);
  });

  it('does not go above total pages', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, totalRecords: 30 }));
    
    // Total pages should be 3
    expect(result.current.totalPages).toBe(3);
    
    act(() => {
      result.current.goToPage(10);
    });
    
    expect(result.current.page).toBe(3);
  });

  it('goToPage navigates to specific page', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.goToPage(5);
    });
    
    expect(result.current.page).toBe(5);
  });

  it('resets page to 1', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, initialPage: 5 }));
    
    expect(result.current.page).toBe(5);
    
    act(() => {
      result.current.resetPage();
    });
    
    expect(result.current.page).toBe(1);
  });

  it('correctly identifies first page', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    expect(result.current.isFirstPage).toBe(true);
    
    act(() => {
      result.current.nextPage();
    });
    
    expect(result.current.isFirstPage).toBe(false);
  });

  it('correctly identifies last page', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, totalRecords: 30 }));
    
    // Go to last page (page 3)
    act(() => {
      result.current.goToPage(3);
    });
    
    expect(result.current.isLastPage).toBe(true);
  });

  it('generates page numbers with ellipsis', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, initialPage: 5 }));
    
    // With 10 pages and current page 5, should have ellipsis
    expect(result.current.pageNumbers).toContain(1);
    expect(result.current.pageNumbers).toContain('...');
    expect(result.current.pageNumbers).toContain(5);
    expect(result.current.pageNumbers).toContain(10);
  });

  it('handles jump to page input', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.setJumpToPage('5');
    });
    
    expect(result.current.jumpToPage).toBe('5');
    
    act(() => {
      result.current.handleJumpToPage();
    });
    
    expect(result.current.page).toBe(5);
    expect(result.current.jumpToPage).toBe(''); // Clears after jump
  });

  it('calls onError when jump input is invalid', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));

    act(() => {
      result.current.setJumpToPage('abc');
    });

    act(() => {
      result.current.handleJumpToPage();
    });

    expect(onError).toHaveBeenCalledWith('请输入有效的页码');
  });

  it('calls onError when jump input is out of range', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));

    act(() => {
      result.current.setJumpToPage('999');
    });

    act(() => {
      result.current.handleJumpToPage();
    });

    expect(onError).toHaveBeenCalledWith('请输入 1 到 10 之间的页码');
  });

  it('handles zero total records', () => {
    const { result } = renderHook(() => usePagination({ ...defaultOptions, totalRecords: 0 }));
    
    expect(result.current.totalPages).toBe(1);
    expect(result.current.isFirstPage).toBe(true);
    expect(result.current.isLastPage).toBe(true);
  });

  it('allows setting page directly', () => {
    const { result } = renderHook(() => usePagination(defaultOptions));
    
    act(() => {
      result.current.setPage(7);
    });
    
    expect(result.current.page).toBe(7);
  });
});
