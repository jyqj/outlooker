import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { batchDeleteAccounts, batchUpdateTags } from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';
import { handleApiError } from '@/lib/error';
import { MESSAGES } from '@/lib/constants';
import { queryKeys } from '@/lib/queryKeys';

export type BatchTagMode = 'add' | 'remove' | 'set';

interface BatchTagModalState {
  isOpen: boolean;
  mode: BatchTagMode;
}

interface DeleteConfirmState {
  isOpen: boolean;
  count: number;
}

/**
 * 批量操作 Hook
 * 处理批量删除和批量标签操作
 */
export function useBatchOperations(
  selectedAccounts: Set<string>,
  onSuccess: () => void
) {
  const queryClient = useQueryClient();
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchTagModal, setBatchTagModal] = useState<BatchTagModalState>({ 
    isOpen: false, 
    mode: 'add' 
  });
  const [batchTags, setBatchTags] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
    isOpen: false,
    count: 0,
  });

  // 打开删除确认对话框
  const openDeleteConfirm = useCallback(() => {
    if (selectedAccounts.size === 0) return;
    setDeleteConfirm({
      isOpen: true,
      count: selectedAccounts.size,
    });
  }, [selectedAccounts.size]);

  // 关闭删除确认对话框
  const closeDeleteConfirm = useCallback(() => {
    setDeleteConfirm({ isOpen: false, count: 0 });
  }, []);

  // 执行批量删除
  const executeBatchDelete = useCallback(async () => {
    if (selectedAccounts.size === 0) return;
    
    setBatchLoading(true);
    try {
      const result = await batchDeleteAccounts(Array.from(selectedAccounts));
      if (result.success) {
        showSuccess(result.message);
        onSuccess();
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts() });
        queryClient.invalidateQueries({ queryKey: queryKeys.tags() });
      } else {
        showError(result.message || MESSAGES.ERROR_BATCH_DELETE_FAILED);
      }
    } catch (e) {
      showError(handleApiError(e, '批量删除失败', MESSAGES.ERROR_BATCH_DELETE_FAILED));
    } finally {
      setBatchLoading(false);
      closeDeleteConfirm();
    }
  }, [selectedAccounts, onSuccess, queryClient, closeDeleteConfirm]);

  // 保持向后兼容的 handleBatchDelete（打开确认对话框）
  const handleBatchDelete = openDeleteConfirm;

  const handleBatchTagSubmit = useCallback(async () => {
    if (selectedAccounts.size === 0) return;
    const tags = batchTags.split(',').map(t => t.trim()).filter(Boolean);
    if (tags.length === 0 && batchTagModal.mode !== 'set') {
      showError(MESSAGES.ERROR_TAG_INPUT_REQUIRED);
      return;
    }

    setBatchLoading(true);
    try {
      const result = await batchUpdateTags(
        Array.from(selectedAccounts), 
        tags, 
        batchTagModal.mode
      );
      if (result.success) {
        showSuccess(result.message);
        closeBatchTagModal();
        queryClient.invalidateQueries({ queryKey: queryKeys.tags() });
      } else {
        showError(result.message || MESSAGES.ERROR_BATCH_TAG_OPERATION_FAILED);
      }
    } catch (e) {
      showError(handleApiError(e, '批量标签操作失败', MESSAGES.ERROR_BATCH_TAG_OPERATION_FAILED));
    } finally {
      setBatchLoading(false);
    }
  }, [selectedAccounts, batchTags, batchTagModal.mode, queryClient]);

  const openBatchTagModal = useCallback((mode: BatchTagMode = 'add') => {
    setBatchTagModal({ isOpen: true, mode });
  }, []);

  const closeBatchTagModal = useCallback(() => {
    setBatchTagModal({ isOpen: false, mode: 'add' });
    setBatchTags('');
  }, []);

  const setTagMode = useCallback((mode: BatchTagMode) => {
    setBatchTagModal(prev => ({ ...prev, mode }));
  }, []);

  return {
    batchLoading,
    batchTagModal,
    batchTags,
    setBatchTags,
    setTagMode,
    handleBatchDelete,
    handleBatchTagSubmit,
    openBatchTagModal,
    closeBatchTagModal,
    // 删除确认对话框状态和方法
    deleteConfirm,
    closeDeleteConfirm,
    executeBatchDelete,
  };
}
