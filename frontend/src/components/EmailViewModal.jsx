import React from 'react';
import { Mail, Calendar, User, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { extractCodeFromMessage } from '../lib/utils';
import { sanitizeHtml } from '../lib/sanitize';
import { Dialog } from './ui/Dialog';
import { Button } from './ui/Button';
import { Skeleton } from './ui/Skeleton';
import VerificationCodeCard from './VerificationCodeCard';

export default function EmailViewModal({ email, isOpen, onClose }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['email-messages', email],
    queryFn: async () => {
      const res = await api.get('/api/messages', {
        params: { email, page: 1, page_size: 1 }
      });
      return res.data;
    },
    enabled: isOpen && !!email,
  });

  const payload = data?.data;
  const message = Array.isArray(payload) ? payload[0] : payload?.items?.[0];
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
            onClick={() => refetch()}
            title="刷新邮件"
            className="hover:bg-primary/10"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 overflow-y-auto flex-1 bg-white dark:bg-gray-950">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-6">
            <div className="relative">
              <Loader2 className="w-16 h-16 text-primary animate-spin" />
              <div className="absolute inset-0 w-16 h-16 border-4 border-primary/20 rounded-full"></div>
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-foreground">正在获取邮件...</p>
              <p className="text-sm text-muted-foreground">请稍候，正在从服务器加载最新邮件</p>
            </div>
          </div>
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
              onClick={() => refetch()}
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
              onClick={() => refetch()}
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
              <div className="space-y-3 text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
                <div className="flex items-start gap-3">
                  <div className="bg-blue-100 dark:bg-blue-900 p-1.5 rounded">
                    <User className="w-4 h-4 text-primary dark:text-blue-300 shrink-0" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="font-semibold text-foreground block mb-1">发件人</span>
                    <div className="text-foreground">
                      <span className="font-medium">{message.sender?.emailAddress?.name || message.from?.emailAddress?.name || '未知'}</span>
                      <br />
                      <span className="text-xs break-all text-gray-600 dark:text-gray-400">
                        {message.sender?.emailAddress?.address || message.from?.emailAddress?.address || '未知'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="bg-blue-100 dark:bg-blue-900 p-1.5 rounded">
                    <Calendar className="w-4 h-4 text-primary dark:text-blue-300 shrink-0" />
                  </div>
                  <div className="flex-1">
                    <span className="font-semibold text-foreground block mb-1">接收时间</span>
                    <span className="text-foreground">
                      {message.receivedDateTime ? new Date(message.receivedDateTime).toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      }) : '未知'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Email Body */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                📧 邮件正文
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
    </Dialog>
  );
}
