import React from 'react';
import { Mail, RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { extractCodeFromMessage } from '@/lib/utils';
import { handleApiError } from '@/lib/error';
import { queryKeys } from '@/lib/queryKeys';
import { useEmailMessagesQuery } from '@/lib/hooks';
import { showSuccess, showError } from '@/lib/toast';
import { Dialog } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { EmailListView } from './EmailListView';
import { EmailDetailView } from './EmailDetailView';
import type { Email, ApiResponse } from '@/types';
import type { EmailViewModalProps, MessagesData } from './types';

/** 每页显示的邮件数量 */
const PAGE_SIZE = 10;

/**
 * 邮件查看模态框容器组件
 * 管理状态、数据获取和子组件编排
 */
export default function EmailViewModal({
  email,
  isOpen,
  onClose,
}: EmailViewModalProps) {
  const queryClient = useQueryClient();
  const [refreshCounter, setRefreshCounter] = React.useState(0);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteId, setDeleteId] = React.useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = React.useState<string | null>(null);
  const [page, setPage] = React.useState(1);

  // 模态框关闭时重置状态
  React.useEffect(() => {
    if (!isOpen) {
      setRefreshCounter(0);
      setDeleteId(null);
      setSelectedMessageId(null);
      setPage(1);
    }
  }, [isOpen, email]);

  // 删除邮件处理
  const handleDeleteEmail = async () => {
    if (!deleteId) return;

    setDeleting(true);
    try {
      const res = await api.delete<ApiResponse<void>>(
        `/api/email/${encodeURIComponent(email)}/${encodeURIComponent(deleteId)}`
      );
      if (res.data.success) {
        showSuccess('邮件已删除');
        // 如果删除的是当前选中的邮件，清除选中状态
        if (deleteId === selectedMessageId) {
          setSelectedMessageId(null);
        }
        queryClient.invalidateQueries({ queryKey: queryKeys.emailMessagesBase(email) });
        setDeleteId(null);
      } else {
        showError(res.data.message || '删除失败');
        setDeleteId(null);
      }
    } catch (e) {
      showError(handleApiError(e, '删除邮件失败', '删除邮件失败'));
      setDeleteId(null);
    } finally {
      setDeleting(false);
    }
  };

  // 获取邮件数据
  const { data, isLoading, isError } = useEmailMessagesQuery(email, {
    refreshCounter,
    enabled: isOpen,
    page,
    pageSize: PAGE_SIZE,
  });

  // 解析响应数据
  const payload = data?.data;
  const messages: Email[] = Array.isArray(payload)
    ? payload
    : (payload as MessagesData)?.items || [];
  const paginationData = !Array.isArray(payload)
    ? (payload as MessagesData)?.pagination
    : null;
  const totalPages = paginationData?.total_pages || 1;

  // 当前选中的邮件（默认选中第一封）
  const selectedMessage = React.useMemo(() => {
    if (selectedMessageId) {
      return messages.find((m) => m.id === selectedMessageId);
    }
    return messages[0];
  }, [messages, selectedMessageId]);

  // 提取验证码
  const verificationCode = selectedMessage
    ? extractCodeFromMessage(selectedMessage)
    : null;

  // 刷新回调
  const handleRefresh = () => setRefreshCounter((value) => value + 1);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-6xl max-h-[90vh] flex flex-col p-0 overflow-hidden bg-background"
    >
      {/* Header */}
      <div className="p-4 border-b bg-muted flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="bg-primary/10 p-2 rounded-lg">
            <Mail className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-lg truncate" title={email}>
              {email}
            </h3>
            <p className="text-xs text-muted-foreground">
              {paginationData
                ? `共 ${paginationData.total} 封邮件`
                : `${messages.length} 封邮件`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            title="刷新邮件"
            aria-label="刷新邮件列表"
            className="hover:bg-primary/10"
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Content - Two Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Email List */}
        <nav
          className="w-80 border-r border-border flex flex-col bg-muted/50"
          aria-label="邮件列表"
        >
          <EmailListView
            messages={messages}
            selectedMessageId={selectedMessageId}
            isLoading={isLoading}
            isError={isError}
            pagination={
              paginationData
                ? {
                    page: paginationData.page,
                    totalPages: paginationData.total_pages,
                    total: paginationData.total,
                  }
                : { page, totalPages, total: messages.length }
            }
            onSelectMessage={setSelectedMessageId}
            onPageChange={setPage}
            onRefresh={handleRefresh}
          />
        </nav>

        {/* Right: Email Detail */}
        <main
          className="flex-1 overflow-y-auto bg-background"
          aria-label="邮件详情"
        >
          {!isLoading && messages.length > 0 && (
            <EmailDetailView
              message={selectedMessage}
              verificationCode={verificationCode}
              deleting={deleting}
              onDelete={setDeleteId}
            />
          )}
        </main>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDeleteEmail}
        title="删除缓存邮件"
        message="确定要从本地缓存中删除这封邮件吗？这不会影响邮箱服务器上的原始邮件。"
        confirmText="删除缓存"
        variant="danger"
        loading={deleting}
      />
    </Dialog>
  );
}
