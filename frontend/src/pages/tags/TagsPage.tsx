import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { deleteTagGlobally, renameTagGlobally, getTagStats } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { showSuccess, showError } from '@/lib/toast';
import type { TagStatItem } from '@/types/api';
import { PickAccountModal } from '@/components/pick-account';

import { useTagModals } from './hooks/useTagModals';
import { TagsPageHeader } from './TagsPageHeader';
import { TagsStatsSection } from './TagsStatsSection';
import { TagsListSection } from './TagsListSection';
import { UntaggedAccountsCard } from './UntaggedAccountsCard';
import { TagDeleteDialog } from './TagDeleteDialog';
import { TagRenameDialog } from './TagRenameDialog';

// Query hook for tag statistics
function useTagStatsQuery() {
  return useQuery({
    queryKey: queryKeys.tagStats(),
    queryFn: () => getTagStats(),
  });
}

// Loading Skeleton
function TagsPageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="p-4">
            <div className="flex items-center gap-3">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="w-20 h-4" />
                <Skeleton className="w-12 h-6" />
              </div>
            </div>
          </Card>
        ))}
      </div>
      <Card className="divide-y">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Skeleton className="w-24 h-6 rounded-full" />
              <Skeleton className="w-32 h-4" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="w-16 h-8" />
              <Skeleton className="w-16 h-8" />
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

export default function TagsPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useTagStatsQuery();
  
  // Use the custom hook for modal state management
  const {
    pickModal,
    openPickModal,
    closePickModal,
    deleteDialog,
    openDeleteDialog,
    closeDeleteDialog,
    setDeleteLoading,
    renameDialog,
    openRenameDialog,
    closeRenameDialog,
    setRenameNewName,
    setRenameLoading,
  } = useTagModals();

  const stats = data?.data;

  // Navigation handlers
  const handleBack = useCallback(() => {
    navigate('/admin');
  }, [navigate]);

  const handleView = useCallback((tagName: string) => {
    navigate(`/admin?tag=${encodeURIComponent(tagName)}`);
  }, [navigate]);

  const handleViewUntagged = useCallback(() => {
    navigate('/admin?untagged=true');
  }, [navigate]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Pick success handler
  const handlePickSuccess = useCallback(() => {
    refetch();
  }, [refetch]);

  // Delete tag handler
  const handleDeleteConfirm = useCallback(async () => {
    setDeleteLoading(true);
    try {
      const result = await deleteTagGlobally(deleteDialog.tagName);
      if (result.success) {
        showSuccess(result.message || '标签已删除');
        refetch();
      } else {
        showError(result.message || '删除标签失败');
      }
    } catch {
      showError('删除标签失败');
    } finally {
      closeDeleteDialog();
    }
  }, [deleteDialog.tagName, setDeleteLoading, closeDeleteDialog, refetch]);

  // Rename tag handler
  const handleRenameConfirm = useCallback(async () => {
    if (!renameDialog.newName.trim() || renameDialog.newName === renameDialog.oldName) {
      showError('请输入新的标签名称');
      return;
    }
    setRenameLoading(true);
    try {
      const result = await renameTagGlobally(renameDialog.oldName, renameDialog.newName.trim());
      if (result.success) {
        showSuccess(result.message || '标签已重命名');
        refetch();
        closeRenameDialog();
      } else {
        showError(result.message || '重命名标签失败');
        setRenameLoading(false);
      }
    } catch {
      showError('重命名标签失败');
      setRenameLoading(false);
    }
  }, [renameDialog.oldName, renameDialog.newName, setRenameLoading, closeRenameDialog, refetch]);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      {/* Header */}
      <TagsPageHeader
        isLoading={isLoading}
        onRefresh={handleRefresh}
        onRandomPick={() => openPickModal('')}
        onBack={handleBack}
      />

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
        {isLoading ? (
          <TagsPageSkeleton />
        ) : isError ? (
          <Card className="p-6 text-center">
            <p className="text-destructive mb-4">加载标签统计失败</p>
            <Button variant="outline" onClick={() => refetch()}>
              重试
            </Button>
          </Card>
        ) : stats ? (
          <>
            {/* Statistics Overview */}
            <TagsStatsSection
              totalAccounts={stats.total_accounts}
              taggedAccounts={stats.tagged_accounts}
              untaggedAccounts={stats.untagged_accounts}
            />

            {/* Tags List */}
            <TagsListSection
              tags={stats.tags}
              isLoading={isLoading}
              onPick={openPickModal}
              onView={handleView}
              onDelete={openDeleteDialog}
              onRename={openRenameDialog}
            />

            {/* Quick Actions for Untagged Accounts */}
            <UntaggedAccountsCard
              count={stats.untagged_accounts}
              onView={handleViewUntagged}
            />
          </>
        ) : null}
      </main>

      {/* Pick Account Modal */}
      <PickAccountModal
        isOpen={pickModal.isOpen}
        preselectedTag={pickModal.preselectedTag}
        availableTags={stats?.tags.map((t: TagStatItem) => t.name) || []}
        onClose={closePickModal}
        onSuccess={handlePickSuccess}
      />

      {/* Delete Tag Confirm Dialog */}
      <TagDeleteDialog
        isOpen={deleteDialog.isOpen}
        tagName={deleteDialog.tagName}
        loading={deleteDialog.loading}
        onConfirm={handleDeleteConfirm}
        onCancel={closeDeleteDialog}
      />

      {/* Rename Tag Dialog */}
      <TagRenameDialog
        isOpen={renameDialog.isOpen}
        oldName={renameDialog.oldName}
        newName={renameDialog.newName}
        loading={renameDialog.loading}
        onNewNameChange={setRenameNewName}
        onConfirm={handleRenameConfirm}
        onCancel={closeRenameDialog}
      />
    </div>
  );
}
