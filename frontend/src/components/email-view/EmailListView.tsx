import { AlertCircle, ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import type { EmailListViewProps } from './types';

/**
 * 邮件列表视图组件
 * 显示邮件列表和分页控件
 */
export function EmailListView({
  messages,
  selectedMessageId,
  isLoading,
  isError,
  pagination,
  onSelectMessage,
  onPageChange,
  onRefresh,
}: EmailListViewProps) {
  const totalPages = pagination?.totalPages || 1;
  const page = pagination?.page || 1;

  // 加载状态
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <LoadingSpinner text="加载中..." size="md" />
      </div>
    );
  }

  // 错误状态
  if (isError) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 space-y-3">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-sm text-destructive text-center">加载失败</p>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          重试
        </Button>
      </div>
    );
  }

  // 空状态
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 space-y-3">
        <Inbox className="w-12 h-12 text-muted-foreground" />
        <p className="text-sm text-muted-foreground text-center">暂无邮件</p>
      </div>
    );
  }

  return (
    <>
      {/* 邮件列表 */}
      <div className="flex-1 overflow-y-auto">
        {messages.map((msg) => {
          const isSelected =
            selectedMessageId === msg.id ||
            (!selectedMessageId && msg.id === messages[0]?.id);

          return (
            <button
              key={msg.id}
              type="button"
              onClick={() => onSelectMessage(msg.id)}
              className={`w-full text-left p-3 border-b border-border cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary ${
                isSelected
                  ? 'bg-primary/10 border-l-2 border-l-primary'
                  : 'hover:bg-muted'
              }`}
              aria-current={isSelected ? 'true' : undefined}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-sm font-medium text-foreground truncate flex-1">
                  {msg.sender?.emailAddress?.name ||
                    msg.sender?.emailAddress?.address ||
                    '未知发件人'}
                </p>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatRelativeTime(msg.receivedDateTime)}
                </span>
              </div>
              <p className="text-sm text-foreground truncate font-medium mb-1">
                {msg.subject || '(无主题)'}
              </p>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {msg.bodyPreview || '(无预览)'}
              </p>
            </button>
          );
        })}
      </div>

      {/* 分页控件 */}
      {totalPages > 1 && (
        <div
          className="p-3 border-t border-border flex items-center justify-between bg-background"
          role="navigation"
          aria-label="邮件分页"
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            aria-label="上一页"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </Button>
          <span className="text-sm text-muted-foreground" aria-live="polite">
            第 {page} 页，共 {totalPages} 页
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            aria-label="下一页"
          >
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      )}
    </>
  );
}
