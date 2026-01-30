import { User, Calendar } from 'lucide-react';
import { formatDateTime, cn } from '@/lib/utils';
import type { Email } from '@/types';

interface EmailMetadataProps {
  /** 邮件对象 */
  email: Email;
  /** 是否显示主题 */
  showSubject?: boolean;
  /** 布局方式 */
  layout?: 'vertical' | 'grid';
  /** 额外的 className */
  className?: string;
}

/**
 * 获取发件人名称
 */
function getSenderName(email: Email): string {
  return (
    email.sender?.emailAddress?.name ||
    email.from?.emailAddress?.name ||
    '未知'
  );
}

/**
 * 获取发件人地址
 */
function getSenderAddress(email: Email): string {
  return (
    email.sender?.emailAddress?.address ||
    email.from?.emailAddress?.address ||
    '未知'
  );
}

/**
 * 邮件元信息展示组件
 * 显示发件人、时间等信息
 */
export function EmailMetadata({
  email,
  showSubject = false,
  layout = 'vertical',
  className,
}: EmailMetadataProps) {
  const senderName = getSenderName(email);
  const senderAddress = getSenderAddress(email);
  const receivedTime = email.receivedDateTime
    ? formatDateTime(email.receivedDateTime)
    : '未知';

  return (
    <div
      className={`space-y-3 text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800 ${className || ''}`}
    >
      {showSubject && (
        <div>
          <h3 className="font-semibold text-foreground mb-2">邮件主题</h3>
          <p className="text-foreground">{email.subject || '(无主题)'}</p>
        </div>
      )}

      <div
        className={cn(
          layout === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 gap-3'
            : 'space-y-3',
          showSubject && 'pt-3 border-t border-gray-200 dark:border-gray-800'
        )}
      >
        {/* 发件人 */}
        <div className="flex items-start gap-3">
          <div className="bg-blue-100 dark:bg-blue-900 p-1.5 rounded">
            <User className="w-4 h-4 text-primary dark:text-blue-300 shrink-0" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-foreground block mb-1">发件人</span>
            <div className="text-foreground">
              <span className="font-medium">{senderName}</span>
              <br />
              <span className="text-xs break-all text-gray-600 dark:text-gray-400">
                {senderAddress}
              </span>
            </div>
          </div>
        </div>

        {/* 接收时间 */}
        <div className="flex items-start gap-3">
          <div className="bg-blue-100 dark:bg-blue-900 p-1.5 rounded">
            <Calendar className="w-4 h-4 text-primary dark:text-blue-300 shrink-0" />
          </div>
          <div className="flex-1">
            <span className="font-semibold text-foreground block mb-1">接收时间</span>
            <span className="text-foreground">{receivedTime}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
