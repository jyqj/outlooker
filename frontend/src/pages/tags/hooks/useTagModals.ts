import { useState, useCallback } from 'react';
import type { PickModalState, DeleteDialogState, RenameDialogState } from '../types';

export function useTagModals() {
  const [pickModal, setPickModal] = useState<PickModalState>({ 
    isOpen: false, 
    preselectedTag: '' 
  });
  
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState>({ 
    isOpen: false, 
    tagName: '', 
    loading: false 
  });
  
  const [renameDialog, setRenameDialog] = useState<RenameDialogState>({ 
    isOpen: false, 
    oldName: '', 
    newName: '', 
    loading: false 
  });

  // Pick modal handlers
  const openPickModal = useCallback((tag = '') => {
    setPickModal({ isOpen: true, preselectedTag: tag });
  }, []);

  const closePickModal = useCallback(() => {
    setPickModal({ isOpen: false, preselectedTag: '' });
  }, []);

  // Delete dialog handlers
  const openDeleteDialog = useCallback((tagName: string) => {
    setDeleteDialog({ isOpen: true, tagName, loading: false });
  }, []);

  const closeDeleteDialog = useCallback(() => {
    setDeleteDialog({ isOpen: false, tagName: '', loading: false });
  }, []);

  const setDeleteLoading = useCallback((loading: boolean) => {
    setDeleteDialog(prev => ({ ...prev, loading }));
  }, []);

  // Rename dialog handlers
  const openRenameDialog = useCallback((tagName: string) => {
    setRenameDialog({ isOpen: true, oldName: tagName, newName: tagName, loading: false });
  }, []);

  const closeRenameDialog = useCallback(() => {
    setRenameDialog({ isOpen: false, oldName: '', newName: '', loading: false });
  }, []);

  const setRenameNewName = useCallback((newName: string) => {
    setRenameDialog(prev => ({ ...prev, newName }));
  }, []);

  const setRenameLoading = useCallback((loading: boolean) => {
    setRenameDialog(prev => ({ ...prev, loading }));
  }, []);

  return {
    // Pick modal
    pickModal,
    openPickModal,
    closePickModal,
    // Delete dialog
    deleteDialog,
    openDeleteDialog,
    closeDeleteDialog,
    setDeleteLoading,
    // Rename dialog
    renameDialog,
    openRenameDialog,
    closeRenameDialog,
    setRenameNewName,
    setRenameLoading,
  };
}
