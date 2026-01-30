import React from 'react';
import { Mail, RefreshCw, AlertCircle, Trash2 } from 'lucide-react';
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
}

export default function EmailViewModal({ email, isOpen, onClose }: EmailViewModalProps) {
  const queryClient = useQueryClient();
  const [refreshCounter, setRefreshCounter] = React.useState(0);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteId, setDeleteId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!isOpen) {
      setRefreshCounter(0);
      setDeleteId(null);
    }
  }, [isOpen, email]);

  const handleDeleteEmail = async () => {
    if (!deleteId) return;
    
    setDeleting(true);
    try {
      const res = await api.delete<ApiResponse<void>>(`/api/email/${encodeURIComponent(email)}/${encodeURIComponent(deleteId)}`);
      if (res.data.success) {
        showSuccess('邮件已删除');
        queryClient.invalidateQueries({ queryKey: queryKeys.emailMessagesBase(email) });
        onClose();
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
  });

  const payload = data?.data;
  const message: Email | undefined = Array.isArray(payload)
    ? payload[0]
    : (payload as MessagesData)?.items?.[0];
  const verificationCode = message ? extractCodeFromMessage(message) : null;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-3xl max-h-[90vh] flex flex-col p-0 overflow-hidden bg-white dark:bg-gray-950"
    >
      {/* Header */}
      <div className="p-5 border-b bg-gray-100 dark:bg-gray-900 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="bg-primary/10 p-2 rounded-lg">
            <Mail className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-lg truncate" title={email}>{email}</h3>
            <p className="text-xs text-muted-foreground">最新邮件预览</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setRefreshCounter((value) => value + 1)}
            title="刷新邮件"
            className="hover:bg-primary/10"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          {message && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setDeleteId(message.id)}
              disabled={deleting}
              title="删除邮件"
              className="hover:bg-destructive/10 hover:text-destructive"
            >
              <Trash2 className={`w-4 h-4 ${deleting ? 'animate-pulse' : ''}`} />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 overflow-y-auto flex-1 bg-white dark:bg-gray-950">
        {isLoading && (
          <LoadingSpinner
            text="正在获取邮件..."
            subText="请稍候，正在从服务器加载最新邮件"
            size="xl"
            showRing
            className="py-20"
          />
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <AlertCircle className="w-12 h-12 text-destructive" />
            <div className="text-center space-y-2">
              <p className="text-destructive font-medium">加载邮件失败</p>
              <p className="text-sm text-muted-foreground">
                请检查账户配置是否正确，或稍后重试
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => setRefreshCounter((value) => value + 1)}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              重新加载
            </Button>
          </div>
        )}

        {!isLoading && !isError && data && !message && (
          <div className="flex flex-col items-center justify-center py-20 space-y-6">
            <div className="bg-gray-100 dark:bg-gray-800 p-6 rounded-full">
              <Mail className="w-16 h-16 text-gray-400 dark:text-gray-500" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-foreground">该邮箱暂无邮件</p>
              <p className="text-sm text-muted-foreground">
                此邮箱中没有找到任何邮件，请稍后再试或检查邮箱配置
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => setRefreshCounter((value) => value + 1)}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              重新加载
            </Button>
          </div>
        )}

        {message && (
          <div className="space-y-6">
            {/* Verification Code */}
            {verificationCode && <VerificationCodeCard code={verificationCode} />}

            {/* Email Meta */}
            <div className="space-y-4 pb-4 border-b border-gray-200 dark:border-gray-800">
              <h2 className="text-2xl font-bold text-foreground leading-tight">
                {message.subject || '(无主题)'}
              </h2>
              <EmailMetadata email={message} />
            </div>

            {/* Email Body */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                邮件正文
              </h3>
              {message.body?.content ? (
                <div className="bg-gray-50 dark:bg-gray-900 p-5 rounded-lg border border-gray-200 dark:border-gray-800 max-h-[500px] overflow-y-auto">
                  {message.body.contentType === 'html' ? (
                    <div
                      className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-a:text-primary [&_*]:text-foreground"
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(message.body.content) }}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">{message.body.content}</pre>
                  )}
                </div>
              ) : (
                <div className="bg-gray-50 dark:bg-gray-900 p-8 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 text-center">
                  <p className="text-gray-500 dark:text-gray-400 text-sm">该邮件无正文内容</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDeleteEmail}
        title="删除邮件"
        message="确定要删除这封邮件吗？此操作不可恢复。"
        confirmText="删除"
        variant="danger"
        loading={deleting}
      />
    </Dialog>
  );
}
