import React from 'react';
import { Mail, RefreshCw, AlertCircle, Trash2, ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { extractCodeFromMessage } from '@/lib/utils';
import { handleApiError } from '@/lib/error';
import { queryKeys } from '@/lib/queryKeys';
import { useEmailMessagesQuery } from '@/lib/hooks';
import { sanitizeHtml } from '@/lib/sanitize';
import { showSuccess, showError } from '@/lib/toast';
import { Dialog } from './ui/Dialog';
import { Button } from './ui/Button';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { LoadingSpinner } from './ui/LoadingSpinner';
import VerificationCodeCard from './VerificationCodeCard';
import { EmailMetadata } from './EmailMetadata';
import type { Email, ApiResponse } from '@/types';

interface EmailViewModalProps {
  email: string;
  isOpen: boolean;
  onClose: () => void;
}

interface MessagesData {
  items?: Email[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

// 每页显示的邮件数量
const PAGE_SIZE = 10;

export default function EmailViewModal({ email, isOpen, onClose }: EmailViewModalProps) {
  const queryClient = useQueryClient();
  const [refreshCounter, setRefreshCounter] = React.useState(0);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteId, setDeleteId] = React.useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = React.useState<string | null>(null);
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    if (!isOpen) {
      setRefreshCounter(0);
      setDeleteId(null);
      setSelectedMessageId(null);
      setPage(1);
    }
  }, [isOpen, email]);

  const handleDeleteEmail = async () => {
    if (!deleteId) return;
    
    setDeleting(true);
    try {
      const res = await api.delete<ApiResponse<void>>(`/api/email/${encodeURIComponent(email)}/${encodeURIComponent(deleteId)}`);
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

  const { data, isLoading, isError } = useEmailMessagesQuery(email, {
    refreshCounter,
    enabled: isOpen,
    page,
    pageSize: PAGE_SIZE,
  });

  const payload = data?.data;
  const messages: Email[] = Array.isArray(payload) 
    ? payload 
    : (payload as MessagesData)?.items || [];
  const pagination = !Array.isArray(payload) ? (payload as MessagesData)?.pagination : null;
  const totalPages = pagination?.total_pages || 1;
  
  // 当前选中的邮件，默认选中第一封
  const selectedMessage = React.useMemo(() => {
    if (selectedMessageId) {
      return messages.find(m => m.id === selectedMessageId);
    }
    return messages[0];
  }, [messages, selectedMessageId]);
  
  const verificationCode = selectedMessage ? extractCodeFromMessage(selectedMessage) : null;

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

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
            <h3 className="font-bold text-lg truncate" title={email}>{email}</h3>
            <p className="text-xs text-muted-foreground">
              {pagination ? `共 ${pagination.total} 封邮件` : `${messages.length} 封邮件`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setRefreshCounter((value) => value + 1)}
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
        <nav className="w-80 border-r border-border flex flex-col bg-muted/50" aria-label="邮件列表">
          {isLoading && (
            <div className="flex-1 flex items-center justify-center">
              <LoadingSpinner text="加载中..." size="md" />
            </div>
          )}

          {isError && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 space-y-3">
              <AlertCircle className="w-8 h-8 text-destructive" />
              <p className="text-sm text-destructive text-center">加载失败</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRefreshCounter((value) => value + 1)}
              >
                重试
              </Button>
            </div>
          )}

          {!isLoading && !isError && messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 space-y-3">
              <Inbox className="w-12 h-12 text-muted-foreground" />
              <p className="text-sm text-muted-foreground text-center">暂无邮件</p>
            </div>
          )}

          {!isLoading && !isError && messages.length > 0 && (
            <>
              <div className="flex-1 overflow-y-auto">
                {messages.map((msg) => (
                  <button
                    key={msg.id}
                    type="button"
                    onClick={() => setSelectedMessageId(msg.id)}
                    className={`w-full text-left p-3 border-b border-border cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary ${
                      (selectedMessageId === msg.id || (!selectedMessageId && msg.id === messages[0]?.id))
                        ? 'bg-primary/10 border-l-2 border-l-primary'
                        : 'hover:bg-muted'
                    }`}
                    aria-current={(selectedMessageId === msg.id || (!selectedMessageId && msg.id === messages[0]?.id)) ? 'true' : undefined}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="text-sm font-medium text-foreground truncate flex-1">
                        {msg.sender?.emailAddress?.name || msg.sender?.emailAddress?.address || '未知发件人'}
                      </p>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTime(msg.receivedDateTime)}
                      </span>
                    </div>
                    <p className="text-sm text-foreground truncate font-medium mb-1">
                      {msg.subject || '(无主题)'}
                    </p>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {msg.bodyPreview || '(无预览)'}
                    </p>
                  </button>
                ))}
              </div>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-3 border-t border-border flex items-center justify-between bg-background" role="navigation" aria-label="邮件分页">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
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
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    aria-label="下一页"
                  >
                    <ChevronRight className="w-4 h-4" aria-hidden="true" />
                  </Button>
                </div>
              )}
            </>
          )}
        </nav>

        {/* Right: Email Detail */}
        <main className="flex-1 overflow-y-auto bg-background" aria-label="邮件详情">
          {!selectedMessage && !isLoading && messages.length > 0 && (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center">
              <Mail className="w-16 h-16 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">选择一封邮件查看详情</p>
            </div>
          )}

          {selectedMessage && (
            <div className="p-6 space-y-6">
              {/* Verification Code */}
              {verificationCode && <VerificationCodeCard code={verificationCode} />}

              {/* Email Meta */}
              <div className="space-y-4 pb-4 border-b border-border">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-xl font-bold text-foreground leading-tight flex-1">
                    {selectedMessage.subject || '(无主题)'}
                  </h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteId(selectedMessage.id)}
                    disabled={deleting}
                    title="删除邮件"
                    aria-label="删除此邮件"
                    className="hover:bg-destructive/10 hover:text-destructive shrink-0"
                  >
                    <Trash2 className={`w-4 h-4 ${deleting ? 'animate-pulse' : ''}`} aria-hidden="true" />
                  </Button>
                </div>
                <EmailMetadata email={selectedMessage} />
              </div>

              {/* Email Body */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                  邮件正文
                </h3>
                {selectedMessage.body?.content ? (
                  <div className="bg-muted p-5 rounded-lg border border-border">
                    {selectedMessage.body.contentType === 'html' ? (
                      <div
                        className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-a:text-primary [&_*]:text-foreground"
                        dangerouslySetInnerHTML={{ __html: sanitizeHtml(selectedMessage.body.content) }}
                      />
                    ) : (
                      <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">{selectedMessage.body.content}</pre>
                    )}
                  </div>
                ) : (
                  <div className="bg-muted p-8 rounded-lg border border-dashed border-border text-center">
                    <p className="text-muted-foreground text-sm">该邮件无正文内容</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

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
