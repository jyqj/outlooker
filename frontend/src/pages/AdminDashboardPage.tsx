import React, { useCallback, useEffect, useState, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import api, { clearAuthTokens } from '@/lib/api';
import { showSuccess, showError } from '@/lib/toast';
import { MESSAGES } from '@/lib/constants';
import { useAccountsQuery, useAccountTagsQuery, useDebounce } from '@/lib/hooks';
import { logError } from '@/lib/utils';
import { handleApiError } from '@/lib/error';
import { queryKeys } from '@/lib/queryKeys';
import { downloadBlob } from '@/lib/download';
import type { Account } from '@/types';
import { isTagsData } from '@/types/api';

// Dashboard sub-components
import { 
  BatchTagModal, 
  SystemOverview, 
  DashboardHeader, 
  DashboardToolbar, 
  AccountsTable,
} from './dashboard/components';
import { 
  useAccountSelection, 
  useBatchOperations, 
  usePagination,
  useDashboardModals
} from './dashboard/hooks';

// Lazy load modals
const ImportModal = React.lazy(() => import('@/components/ImportModal'));
const EmailViewModal = React.lazy(() => import('@/components/email-view').then(m => ({ default: m.EmailViewModal })));
const TagManageModal = React.lazy(() => import('@/components/TagManageModal'));

// Import ConfirmDialog
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Search state
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 500);

  // Modals state
  const modals = useDashboardModals();

  // Data queries
  const { data: tagsData } = useAccountTagsQuery();
  const accountTagsMap: Record<string, string[]> = 
    isTagsData(tagsData?.data) ? tagsData.data.accounts : {};

  // Total records state for pagination
  const [totalRecords, setTotalRecords] = useState(0);

  // Pagination hook
  const pagination = usePagination({
    initialPage: 1,
    initialPageSize: 10,
    totalRecords,
    onError: showError,
  });

  // Fetch accounts with pagination
  const { data, isLoading, isError } = useAccountsQuery({ 
    page: pagination.page, 
    search: debouncedSearch, 
    pageSize: pagination.pageSize 
  });

  const accounts: Account[] = data?.data?.items || [];
  
  // Update total records when data changes
  useEffect(() => {
    const total = data?.data?.pagination?.total || data?.data?.total;
    if (typeof total === 'number') {
      setTotalRecords(total);
    }
  }, [data]);

  // Account selection hook
  const selection = useAccountSelection(accounts.map(a => a.email));

  // Batch operations hook
  const batchOps = useBatchOperations(
    selection.selectedAccounts,
    selection.clearSelection
  );

  // Reset page when search changes
  useEffect(() => {
    pagination.resetPage();
  }, [debouncedSearch, pagination.resetPage]);

  // Clear selection when pagination changes
  useEffect(() => {
    selection.clearSelection();
  }, [pagination.page, pagination.pageSize, selection.clearSelection]);

  // Handlers
  const handleLogout = useCallback(async () => {
    try {
      await api.post('/api/admin/logout', {});
    } catch (e) {
      logError('退出登录失败', e);
    } finally {
      clearAuthTokens();
      navigate('/admin/login');
    }
  }, [navigate]);

  const handleExport = useCallback(async () => {
    modals.setExporting(true);
    try {
      const res = await api.get('/api/export', { responseType: 'blob' });
      downloadBlob(new Blob([res.data as BlobPart]), 'outlook_accounts.txt');
      showSuccess(MESSAGES.SUCCESS_EXPORT);
    } catch (e: unknown) {
      showError(handleApiError(e, '导出失败', MESSAGES.ERROR_EXPORT_FAILED));
    } finally {
      modals.setExporting(false);
    }
  }, [modals]);

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.accounts() });
  }, [queryClient]);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      <DashboardHeader onLogout={handleLogout} />

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <DashboardToolbar
          search={search}
          onSearchChange={setSearch}
          selectedCount={selection.selectedCount}
          batchLoading={batchOps.batchLoading}
          exporting={modals.exporting}
          onBatchDelete={batchOps.handleBatchDelete}
          onOpenBatchTagModal={() => batchOps.openBatchTagModal('add')}
          onClearSelection={selection.clearSelection}
          onImport={modals.openImport}
          onExport={handleExport}
          onRefresh={handleRefresh}
        />

        <SystemOverview />

        <AccountsTable
          accounts={accounts}
          accountTagsMap={accountTagsMap}
          isLoading={isLoading}
          isError={isError}
          debouncedSearch={debouncedSearch}
          selection={selection}
          pagination={pagination}
          onViewEmails={modals.openEmailView}
          onManageTags={modals.openTagManage}
          onRefresh={handleRefresh}
          onImport={modals.openImport}
        />
      </main>

      {/* Modals with Suspense */}
      <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">正在加载资源...</div>}>
        <ImportModal
          isOpen={modals.showImport}
          onClose={modals.closeImport}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: queryKeys.accounts() })}
        />

        {modals.selectedEmail && (
          <EmailViewModal
            email={modals.selectedEmail}
            isOpen={!!modals.selectedEmail}
            onClose={modals.closeEmailView}
          />
        )}

        {modals.tagModal.isOpen && modals.tagModal.email && (
          <TagManageModal
            email={modals.tagModal.email}
            currentTags={accountTagsMap[modals.tagModal.email]}
            isOpen={modals.tagModal.isOpen}
            onClose={modals.closeTagManage}
            onSuccess={() => queryClient.invalidateQueries({ queryKey: queryKeys.tags() })}
          />
        )}
      </Suspense>

      {/* Batch Tag Modal */}
      <BatchTagModal
        isOpen={batchOps.batchTagModal.isOpen}
        mode={batchOps.batchTagModal.mode}
        selectedCount={selection.selectedCount}
        batchTags={batchOps.batchTags}
        loading={batchOps.batchLoading}
        onTagsChange={batchOps.setBatchTags}
        onModeChange={batchOps.setTagMode}
        onSubmit={batchOps.handleBatchTagSubmit}
        onClose={batchOps.closeBatchTagModal}
      />

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={batchOps.deleteConfirm.isOpen}
        onClose={batchOps.closeDeleteConfirm}
        onConfirm={batchOps.executeBatchDelete}
        title="确认删除"
        message={`确定要删除选中的 ${batchOps.deleteConfirm.count} 个账户吗？此操作不可恢复。`}
        confirmText="删除"
        cancelText="取消"
        variant="danger"
        loading={batchOps.batchLoading}
      />
    </div>
  );
}
