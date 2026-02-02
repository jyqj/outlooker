import { sanitizeHtml } from '@/lib/sanitize';
import type { EmailBodyProps } from './types';

/**
 * 邮件正文渲染组件
 * 处理 HTML 和纯文本两种格式，使用 sanitizeHtml 进行安全渲染
 */
export function EmailBody({ body }: EmailBodyProps) {
  if (!body?.content) {
    return (
      <div className="bg-muted p-8 rounded-lg border border-dashed border-border text-center">
        <p className="text-muted-foreground text-sm">该邮件无正文内容</p>
      </div>
    );
  }

  if (body.contentType === 'html') {
    return (
      <div className="bg-muted p-5 rounded-lg border border-border">
        <div
          className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-a:text-primary [&_*]:text-foreground"
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(body.content) }}
        />
      </div>
    );
  }

  return (
    <div className="bg-muted p-5 rounded-lg border border-border">
      <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">
        {body.content}
      </pre>
    </div>
  );
}
