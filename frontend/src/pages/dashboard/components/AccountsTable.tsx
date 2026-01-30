import { Inbox, XCircle, RefreshCw, Upload, CheckSquare, Square } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { AccountTableRow } from './AccountTableRow';
import { Pagination } from './Pagination';
import type { Account } from '@/types';
import type { PaginationState } from '../hooks/usePagination';
import type { AccountSelectionState } from '../hooks/useAccountSelection';

interface AccountsTableProps {
  accounts: Account[];
  accountTagsMap: Record<string, string[]>;
  isLoading: boolean;
  isError: boolean;
  debouncedSearch: string;
  selection: AccountSelectionState;
  pagination: PaginationState;
  onViewEmails: (email: string) => void;
  onManageTags: (email: string) => void;
  onRefresh: () => void;
  onImport: () => void;
}

export function AccountsTable({
  accounts,
  accountTagsMap,
  isLoading,
  isError,
  debouncedSearch,
  selection,
  pagination,
  onViewEmails,
  onManageTags,
  onRefresh,
  onImport,
}: AccountsTableProps) {
  const {
    isAllSelected,
    selectedAccounts,
    toggleSelectAll,
    toggleSelectAccount,
  } = selection;

  const {
    page,
    pageSize,
    totalPages,
    totalRecords,
    jumpToPage,
    pageNumbers,
    isFirstPage,
    isLastPage,
    goToPage: onPageChange,
    handlePageSizeChange: onPageSizeChange,
    setJumpToPage: onJumpToPageChange,
    handleJumpToPage: onJumpToPage,
    nextPage: onNextPage,
    prevPage: onPrevPage,
  } = pagination;

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto" role="region" aria-label="账户列表">
        <table className="w-full text-left text-sm" role="grid" aria-label="邮箱账户列表">
          <thead className="bg-muted text-muted-foreground font-medium border-b">
            <tr role="row">
              <th className="px-4 py-4 w-12" scope="col">
                <button
                  onClick={toggleSelectAll}
                  className="p-1 hover:bg-muted-foreground/10 rounded focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                  title={isAllSelected ? '取消全选' : '全选'}
                  aria-label={isAllSelected ? '取消全选所有账户' : '全选所有账户'}
                  aria-pressed={isAllSelected}
                  type="button"
                >
                  {isAllSelected ? (
                    <CheckSquare className="w-4 h-4 text-primary" aria-hidden="true" />
                  ) : (
                    <Square className="w-4 h-4" aria-hidden="true" />
                  )}
                </button>
              </th>
              <th className="px-4 py-4" scope="col">邮箱账户</th>
              <th className="px-4 py-4" scope="col">标签</th>
              <th className="px-4 py-4 text-right" scope="col">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-4"><Skeleton className="h-4 w-4" /></td>
                  <td className="px-4 py-4"><Skeleton className="h-4 w-48" /></td>
                  <td className="px-4 py-4"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-4 text-right"><Skeleton className="h-8 w-16 ml-auto" /></td>
                </tr>
              ))
            ) : isError ? (
              <tr>
                <td colSpan={4} className="px-6 py-12">
                  <div className="flex flex-col items-center justify-center space-y-4">
                    <XCircle className="w-12 h-12 text-destructive" />
                    <div className="text-center space-y-2">
                      <p className="text-destructive font-medium">加载账户列表失败</p>
                      <p className="text-sm text-muted-foreground">请检查网络连接或稍后重试</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={onRefresh} className="gap-2">
                      <RefreshCw className="w-4 h-4" />重新加载
                    </Button>
                  </div>
                </td>
              </tr>
            ) : accounts.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-12">
                  <div className="flex flex-col items-center justify-center space-y-4">
                    <Inbox className="w-16 h-16 text-muted-foreground/40" />
                    <div className="text-center space-y-2">
                      <p className="text-muted-foreground font-semibold text-base">
                        {debouncedSearch ? '未找到匹配的账户' : '暂无账户数据'}
                      </p>
                      <p className="text-sm text-muted-foreground/80">
                        {debouncedSearch ? '尝试使用其他关键词搜索' : '点击"导入"按钮添加账户'}
                      </p>
                    </div>
                    {!debouncedSearch && (
                      <Button onClick={onImport} className="gap-2">
                        <Upload className="w-4 h-4" />导入账户
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              accounts.map((account) => (
                <AccountTableRow
                  key={account.email}
                  account={account}
                  isSelected={selectedAccounts.has(account.email)}
                  tags={accountTagsMap[account.email] || []}
                  onToggleSelect={toggleSelectAccount}
                  onViewEmails={onViewEmails}
                  onManageTags={onManageTags}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        pageSize={pageSize}
        totalPages={totalPages}
        totalRecords={totalRecords}
        jumpToPage={jumpToPage}
        pageNumbers={pageNumbers}
        isFirstPage={isFirstPage}
        isLastPage={isLastPage}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        onJumpToPageChange={onJumpToPageChange}
        onJumpToPage={onJumpToPage}
        onNextPage={onNextPage}
        onPrevPage={onPrevPage}
      />
    </Card>
  );
}
