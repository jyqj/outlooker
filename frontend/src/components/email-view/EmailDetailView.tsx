import { Mail, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { EmailMetadata } from '../EmailMetadata';
import VerificationCodeCard from '../VerificationCodeCard';
import { EmailBody } from './EmailBody';
import type { EmailDetailViewProps } from './types';

/**
 * 邮件详情视图组件
 * 显示选中邮件的完整内容，包括验证码、元数据和正文
 */
export function EmailDetailView({
  message,
  verificationCode,
  deleting,
  onDelete,
}: EmailDetailViewProps) {
  // 未选中邮件时显示占位符
  if (!message) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <Mail className="w-16 h-16 text-muted-foreground/50 mb-4" />
        <p className="text-muted-foreground">选择一封邮件查看详情</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* 验证码卡片 */}
      {verificationCode && <VerificationCodeCard code={verificationCode} />}

      {/* 邮件元信息 */}
      <div className="space-y-4 pb-4 border-b border-border">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold text-foreground leading-tight flex-1">
            {message.subject || '(无主题)'}
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(message.id)}
            disabled={deleting}
            title="删除邮件"
            aria-label="删除此邮件"
            className="hover:bg-destructive/10 hover:text-destructive shrink-0"
          >
            <Trash2
              className={`w-4 h-4 ${deleting ? 'animate-pulse' : ''}`}
              aria-hidden="true"
            />
          </Button>
        </div>
        <EmailMetadata email={message} />
      </div>

      {/* 邮件正文 */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          邮件正文
        </h3>
        <EmailBody body={message.body} />
      </div>
    </div>
  );
}
