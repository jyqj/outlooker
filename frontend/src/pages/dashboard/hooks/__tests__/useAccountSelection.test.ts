import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAccountSelection } from '../useAccountSelection';

describe('useAccountSelection', () => {
  const mockEmails = ['a@example.com', 'b@example.com', 'c@example.com'];

  it('initializes with empty selection', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    expect(result.current.selectedAccounts.size).toBe(0);
    expect(result.current.selectedCount).toBe(0);
    expect(result.current.isAllSelected).toBe(false);
  });

  it('toggles single account selection', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
    });
    
    expect(result.current.selectedAccounts.has('a@example.com')).toBe(true);
    expect(result.current.selectedCount).toBe(1);
  });

  it('toggles off already selected account', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
    });
    
    expect(result.current.selectedAccounts.has('a@example.com')).toBe(true);
    
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
    });
    
    expect(result.current.selectedAccounts.has('a@example.com')).toBe(false);
    expect(result.current.selectedCount).toBe(0);
  });

  it('selects all accounts when toggleSelectAll is called', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    act(() => {
      result.current.toggleSelectAll();
    });
    
    expect(result.current.selectedCount).toBe(3);
    expect(result.current.isAllSelected).toBe(true);
    expect(result.current.selectedAccounts.has('a@example.com')).toBe(true);
    expect(result.current.selectedAccounts.has('b@example.com')).toBe(true);
    expect(result.current.selectedAccounts.has('c@example.com')).toBe(true);
  });

  it('deselects all when toggleSelectAll is called with all selected', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    // Select all first
    act(() => {
      result.current.toggleSelectAll();
    });
    
    expect(result.current.isAllSelected).toBe(true);
    
    // Toggle again to deselect all
    act(() => {
      result.current.toggleSelectAll();
    });
    
    expect(result.current.selectedCount).toBe(0);
    expect(result.current.isAllSelected).toBe(false);
  });

  it('clears selection', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
      result.current.toggleSelectAccount('b@example.com');
    });
    
    expect(result.current.selectedCount).toBe(2);
    
    act(() => {
      result.current.clearSelection();
    });
    
    expect(result.current.selectedCount).toBe(0);
    expect(result.current.selectedAccounts.size).toBe(0);
  });

  it('handles empty account list', () => {
    const { result } = renderHook(() => useAccountSelection([]));
    
    expect(result.current.selectedCount).toBe(0);
    expect(result.current.isAllSelected).toBe(false);
    
    // Toggle all on empty list should not cause errors
    act(() => {
      result.current.toggleSelectAll();
    });
    
    expect(result.current.selectedCount).toBe(0);
  });

  it('correctly reports isAllSelected', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    // Select 2 of 3
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
      result.current.toggleSelectAccount('b@example.com');
    });
    
    expect(result.current.isAllSelected).toBe(false);
    
    // Select the last one
    act(() => {
      result.current.toggleSelectAccount('c@example.com');
    });
    
    expect(result.current.isAllSelected).toBe(true);
  });

  it('allows selecting multiple accounts independently', () => {
    const { result } = renderHook(() => useAccountSelection(mockEmails));
    
    act(() => {
      result.current.toggleSelectAccount('a@example.com');
    });
    
    act(() => {
      result.current.toggleSelectAccount('c@example.com');
    });
    
    expect(result.current.selectedCount).toBe(2);
    expect(result.current.selectedAccounts.has('a@example.com')).toBe(true);
    expect(result.current.selectedAccounts.has('b@example.com')).toBe(false);
    expect(result.current.selectedAccounts.has('c@example.com')).toBe(true);
  });
});
