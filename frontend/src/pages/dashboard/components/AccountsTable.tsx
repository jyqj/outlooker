import * as React from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Inbox, XCircle, RefreshCw, Upload, CheckSquare, Square, Mail, Tag } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { AccountTableRow } from './AccountTableRow';
import { Pagination } from './Pagination';
import type { Account } from '@/types';
import type { PaginationState } from '../hooks/usePagination';
import type { AccountSelectionState } from '../hooks/useAccountSelection';

// Threshold for enabling virtual scrolling
const VIRTUALIZATION_THRESHOLD = 50;
// Estimated row height for virtualization
const ROW_HEIGHT = 72;

// Virtualized row component (div-based for virtual scrolling)
interface VirtualizedRowProps {
  account: Account;
  isSelected: boolean;
  tags: string[];
  onToggleSelect: (email: string) => void;
  onViewEmails: (email: string) => void;
  onManageTags: (email: string) => void;
  style?: React.CSSProperties;
}

const VirtualizedAccountRow = React.memo(function VirtualizedAccountRow({
  account,
  isSelected,
  tags,
  onToggleSelect,
  onViewEmails,
  onManageTags,
  style,
}: VirtualizedRowProps) {
  const isUsed = typeof account.is_used === 'boolean' ? account.is_used : null;
  const lastUsedAt = account.last_used_at;

  return (
    <div
      style={style}
      className={`flex items-center border-b hover:bg-muted/80 transition-colors ${isSelected ? 'bg-primary/5' : ''}`}
      role="row"
      aria-selected={isSelected}
    >
      {/* Checkbox column */}
      <div className="px-4 py-4 w-12 flex-shrink-0" role="gridcell">
        <button
          onClick={() => onToggleSelect(account.email)}
          className="p-1 hover:bg-muted-foreground/10 rounded focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label={isSelected ? `取消选择 ${account.email}` : `选择 ${account.email}`}
          aria-pressed={isSelected}
          type="button"
        >
          {isSelected ? (
            <CheckSquare className="w-4 h-4 text-primary" aria-hidden="true" />
          ) : (
            <Square className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
          )}
        </button>
      </div>
      {/* Email column */}
      <div className="px-4 py-4 flex-1 min-w-0 font-medium" role="gridcell">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="truncate">{account.email}</span>
            {isUsed !== null && (
              <Badge
                variant={isUsed ? 'outline' : 'secondary'}
                className="text-[11px] px-2 py-0.5 rounded-full flex-shrink-0"
                aria-label={isUsed ? '已使用' : '未使用'}
              >
                {isUsed ? '已使用(公共池)' : '未使用(公共池)'}
              </Badge>
            )}
          </div>
          {isUsed && lastUsedAt && (
            <span className="text-xs text-muted-foreground">
              最后使用：{lastUsedAt}
            </span>
          )}
        </div>
      </div>
      {/* Tags column */}
      <div className="px-4 py-4 w-48 flex-shrink-0" role="gridcell">
        <div className="flex gap-1 flex-wrap" role="list" aria-label="账户标签">
          {tags.map(tag => (
            <Badge key={tag} variant="secondary" className="text-xs" role="listitem">
              {tag}
            </Badge>
          ))}
          {tags.length === 0 && (
            <span className="text-muted-foreground italic text-xs">无标签</span>
          )}
        </div>
      </div>
      {/* Actions column */}
      <div className="px-4 py-4 w-24 flex-shrink-0 text-right" role="gridcell">
        <div className="flex gap-2 justify-end" role="group" aria-label="账户操作">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onViewEmails(account.email)}
            className="h-8 w-8 text-muted-foreground hover:text-primary"
            title="查看邮件"
            aria-label={`查看 ${account.email} 的邮件`}
          >
            <Mail className="w-4 h-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-green-600"
            title="管理标签"
            aria-label={`管理 ${account.email} 的标签`}
            onClick={() => onManageTags(account.email)}
          >
            <Tag className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
});

VirtualizedAccountRow.displayName = 'VirtualizedAccountRow';

// Virtualized table body component
interface VirtualizedTableBodyProps {
  accounts: Account[];
  accountTagsMap: Record<string, string[]>;
  selectedAccounts: Set<string>;
  toggleSelectAccount: (email: string) => void;
  onViewEmails: (email: string) => void;
  onManageTags: (email: string) => void;
}

function VirtualizedTableBody({
  accounts,
  accountTagsMap,
  selectedAccounts,
  toggleSelectAccount,
  onViewEmails,
  onManageTags,
}: VirtualizedTableBodyProps) {
  const parentRef = React.useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: accounts.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
  });

  return (
    <div
      ref={parentRef}
      className="h-[600px] overflow-auto"
      role="rowgroup"
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const account = accounts[virtualRow.index];
          return (
            <VirtualizedAccountRow
              key={account.email}
              account={account}
              isSelected={selectedAccounts.has(account.email)}
              tags={accountTagsMap[account.email] || []}
              onToggleSelect={toggleSelectAccount}
              onViewEmails={onViewEmails}
              onManageTags={onManageTags}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

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
  /** Enable virtual scrolling for large lists (auto-enabled when > VIRTUALIZATION_THRESHOLD items) */
  enableVirtualization?: boolean | 'auto';
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
  enableVirtualization = 'auto',
}: AccountsTableProps) {
  const {
    isAllSelected,
    selectedAccounts,
    toggleSelectAll,
    toggleSelectAccount,
  } = selection;

  // Determine if virtual scrolling should be used
  const shouldVirtualize = enableVirtualization === true || 
    (enableVirtualization === 'auto' && accounts.length >= VIRTUALIZATION_THRESHOLD);

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

  // Render virtualized header (div-based)
  const renderVirtualizedHeader = () => (
    <div className="flex items-center bg-muted text-muted-foreground font-medium border-b text-sm" role="row">
      <div className="px-4 py-4 w-12 flex-shrink-0" role="columnheader">
        <button
          onClick={toggleSelectAll}
          className="p-1 hover:bg-muted-foreground/10 rounded focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          title={isAllSelected ? '取消全选当前页' : `全选当前页 (${accounts.length} 个账户)`}
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
      </div>
      <div className="px-4 py-4 flex-1" role="columnheader">邮箱账户</div>
      <div className="px-4 py-4 w-48 flex-shrink-0" role="columnheader">标签</div>
      <div className="px-4 py-4 w-24 flex-shrink-0 text-right" role="columnheader">操作</div>
    </div>
  );

  return (
    <Card className="overflow-hidden">
      {/* 水平滚动容器，带有渐变遮罩提示 */}
      <div className="relative">
        {/* 右侧渐变遮罩提示可滚动 - 仅在移动端显示 */}
        <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-card to-transparent pointer-events-none z-10 md:hidden" aria-hidden="true" />
        <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent" role="region" aria-label="账户列表，可水平滚动查看更多内容">
          
          {/* Virtualized view for large datasets */}
          {shouldVirtualize && !isLoading && !isError && accounts.length > 0 ? (
            <div role="grid" aria-label="邮箱账户列表" className="text-sm">
              {renderVirtualizedHeader()}
              <VirtualizedTableBody
                accounts={accounts}
                accountTagsMap={accountTagsMap}
                selectedAccounts={selectedAccounts}
                toggleSelectAccount={toggleSelectAccount}
                onViewEmails={onViewEmails}
                onManageTags={onManageTags}
              />
            </div>
          ) : (
            /* Standard table view */
            <table className="w-full text-left text-sm" role="grid" aria-label="邮箱账户列表">
              <thead className="bg-muted text-muted-foreground font-medium border-b">
                <tr role="row">
                  <th className="px-4 py-4 w-12" scope="col">
                    <button
                      onClick={toggleSelectAll}
                      className="p-1 hover:bg-muted-foreground/10 rounded focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                      title={isAllSelected ? '取消全选当前页' : `全选当前页 (${accounts.length} 个账户)`}
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
          )}
        </div>
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
