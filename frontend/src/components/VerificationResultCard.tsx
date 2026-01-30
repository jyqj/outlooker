import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import VerificationCodeCard from '@/components/VerificationCodeCard';
import { EmailMetadata } from '@/components/EmailMetadata';
import { sanitizeHtml } from '@/lib/sanitize';
import type { Email } from '@/types';

export interface EmailResult extends Email {
  extractedCode: string | null;
}

interface VerificationResultCardProps {
  result: EmailResult;
  onRefresh: () => void;
}

export function VerificationResultCard({ result, onRefresh }: VerificationResultCardProps) {
  return (
    <Card className="shadow-md">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">验证码</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 验证码高亮区 */}
        <VerificationCodeCard
          code={result.extractedCode}
          showFallback
        />

        {/* 邮件元信息 */}
        <EmailMetadata email={result} showSubject layout="grid" />

        {/* 邮件正文 */}
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            邮件正文
          </h3>
          <div className="bg-gray-50 dark:bg-gray-900 p-5 rounded-lg border border-gray-200 dark:border-gray-800 max-h-96 overflow-y-auto">
            {result.body?.contentType === 'html' ? (
              <div
                className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-a:text-primary [&_*]:text-foreground"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(result.body.content) }}
              />
            ) : (
              <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">
                {result.body?.content || '(无内容)'}
              </pre>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
