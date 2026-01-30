import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useBatchOperations } from '../useBatchOperations';
import * as api from '@/lib/api';
import React from 'react';

vi.mock('@/lib/api', () => ({
  batchDeleteAccounts: vi.fn(),
  batchUpdateTags: vi.fn(),
}));

vi.mock('@/lib/toast', () => ({
  showSuccess: vi.fn(),
  showError: vi.fn(),
}));

vi.mock('@/lib/utils', () => ({
  logError: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useBatchOperations', () => {
  const selectedAccounts = new Set(['a@example.com', 'b@example.com']);
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with default state', () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    expect(result.current.batchLoading).toBe(false);
    expect(result.current.batchTagModal.isOpen).toBe(false);
    expect(result.current.batchTagModal.mode).toBe('add');
    expect(result.current.batchTags).toBe('');
  });

  it('opens batch tag modal with specified mode', () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.openBatchTagModal('remove');
    });
    
    expect(result.current.batchTagModal.isOpen).toBe(true);
    expect(result.current.batchTagModal.mode).toBe('remove');
  });

  it('closes batch tag modal and resets state', () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    // Open modal and set tags
    act(() => {
      result.current.openBatchTagModal('add');
      result.current.setBatchTags('VIP, test');
    });
    
    expect(result.current.batchTagModal.isOpen).toBe(true);
    expect(result.current.batchTags).toBe('VIP, test');
    
    // Close modal
    act(() => {
      result.current.closeBatchTagModal();
    });
    
    expect(result.current.batchTagModal.isOpen).toBe(false);
    expect(result.current.batchTags).toBe('');
  });

  it('changes tag mode', () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.openBatchTagModal('add');
    });
    
    expect(result.current.batchTagModal.mode).toBe('add');
    
    act(() => {
      result.current.setTagMode('set');
    });
    
    expect(result.current.batchTagModal.mode).toBe('set');
  });

  it('sets batch tags', () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.setBatchTags('tag1, tag2, tag3');
    });
    
    expect(result.current.batchTags).toBe('tag1, tag2, tag3');
  });

  it('handles batch delete success', async () => {
    (api.batchDeleteAccounts as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      success: true,
      message: '删除成功',
    });

    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.handleBatchDelete();
    });

    expect(result.current.deleteConfirm.isOpen).toBe(true);
    expect(result.current.deleteConfirm.count).toBe(2);

    await act(async () => {
      await result.current.executeBatchDelete();
    });
    
    expect(api.batchDeleteAccounts).toHaveBeenCalledWith(['a@example.com', 'b@example.com']);
    expect(mockOnSuccess).toHaveBeenCalled();
  });

  it('does not delete when user closes confirmation', async () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.handleBatchDelete();
    });

    act(() => {
      result.current.closeDeleteConfirm();
    });
    
    expect(api.batchDeleteAccounts).not.toHaveBeenCalled();
  });

  it('handles batch tag submit success', async () => {
    (api.batchUpdateTags as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      success: true,
      message: '标签更新成功',
    });

    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.openBatchTagModal('add');
      result.current.setBatchTags('VIP, Premium');
    });
    
    await act(async () => {
      await result.current.handleBatchTagSubmit();
    });
    
    expect(api.batchUpdateTags).toHaveBeenCalledWith(
      ['a@example.com', 'b@example.com'],
      ['VIP', 'Premium'],
      'add'
    );
    
    // Modal should be closed after success
    await waitFor(() => {
      expect(result.current.batchTagModal.isOpen).toBe(false);
    });
  });

  it('does not submit when no accounts selected', async () => {
    const emptySet = new Set<string>();
    
    const { result } = renderHook(
      () => useBatchOperations(emptySet, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    act(() => {
      result.current.openBatchTagModal('add');
      result.current.setBatchTags('test');
    });
    
    await act(async () => {
      await result.current.handleBatchTagSubmit();
    });
    
    expect(api.batchUpdateTags).not.toHaveBeenCalled();
  });

  it('resets loading state after batch delete', async () => {
    (api.batchDeleteAccounts as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      success: true,
      message: '删除成功',
    });

    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    expect(result.current.batchLoading).toBe(false);
    
    await act(async () => {
      result.current.handleBatchDelete();
      await result.current.executeBatchDelete();
    });
    
    // Loading should be false after operation completes
    expect(result.current.batchLoading).toBe(false);
  });

  it('opens modal with add mode when mode not specified', async () => {
    const { result } = renderHook(
      () => useBatchOperations(selectedAccounts, mockOnSuccess),
      { wrapper: createWrapper() }
    );
    
    await act(async () => {
      result.current.openBatchTagModal('add');
    });
    
    expect(result.current.batchTagModal.isOpen).toBe(true);
    expect(result.current.batchTagModal.mode).toBe('add');
  });
});
