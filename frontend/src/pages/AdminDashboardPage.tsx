import React, { useCallback, useEffect, useState, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  SystemOverview, 
  DashboardHeader, 
  DashboardToolbar, 
  AccountsTable,
  DashboardCharts,
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
const BatchTagModal = React.lazy(() => import('./dashboard/components/BatchTagModal'));

// Import ConfirmDialog
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

export default function AdminDashboardPage() {
  const { t } = useTranslation();
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

  const [healthChecking, setHealthChecking] = useState(false);
  const handleHealthCheck = useCallback(async () => {
    setHealthChecking(true);
    try {
      const res = await api.post('/api/accounts/health-check');
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardSummary() });
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts() });
      const total = res.data?.data?.total ?? 0;
      showSuccess(t('dashboard.healthCheck.success', { total }));
    } catch { showError(t('dashboard.healthCheck.failed')); }
    finally { setHealthChecking(false); }
  }, [queryClient, t]);

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
          healthChecking={healthChecking}
          onBatchDelete={batchOps.handleBatchDelete}
          onOpenBatchTagModal={() => batchOps.openBatchTagModal('add')}
          onClearSelection={selection.clearSelection}
          onImport={modals.openImport}
          onExport={handleExport}
          onRefresh={handleRefresh}
          onHealthCheck={handleHealthCheck}
        />

        <SystemOverview />

        <DashboardCharts />

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
      <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">{t('common.loadingResource')}</div>}>
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

        {/* Batch Tag Modal */}
        {batchOps.batchTagModal.isOpen && (
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
        )}
      </Suspense>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={batchOps.deleteConfirm.isOpen}
        onClose={batchOps.closeDeleteConfirm}
        onConfirm={batchOps.executeBatchDelete}
        title={t('dashboard.confirm.deleteTitle')}
        message={t('dashboard.confirm.deleteMessage', { count: batchOps.deleteConfirm.count })}
        confirmText={t('dashboard.confirm.deleteButton')}
        cancelText={t('dashboard.confirm.cancelButton')}
        variant="danger"
        loading={batchOps.batchLoading}
      />
    </div>
  );
}
