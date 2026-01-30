import { AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export function LoadingCard({ message = '正在获取邮件...', subMessage = '请稍候' }: { message?: string, subMessage?: string }) {
  return (
    <Card className="shadow-md">
      <CardContent className="py-12">
        <LoadingSpinner text={message} subText={subMessage} size="lg" showRing />
      </CardContent>
    </Card>
  );
}

export function ErrorCard({ error, subMessage }: { error: string, subMessage?: string }) {
  return (
    <Card className="shadow-md border-destructive/50">
      <CardContent className="py-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-destructive">{error}</p>
            <p className="text-sm text-muted-foreground mt-1">
              {subMessage || '请检查邮箱地址是否正确，或联系管理员确认该邮箱已配置'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
