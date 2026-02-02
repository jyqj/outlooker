import { XCircle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import type { UntaggedAccountsCardProps } from './types';

export function UntaggedAccountsCard({ count, onView }: UntaggedAccountsCardProps) {
  if (count <= 0) {
    return null;
  }

  return (
    <Card className="p-4 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-600 dark:text-amber-400">
            <XCircle className="w-5 h-5" />
          </div>
          <div>
            <p className="font-medium">有 {count} 个账户尚未标记</p>
            <p className="text-sm text-muted-foreground">
              这些账户可以被任何标签的取号操作选中
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onView}
          className="gap-1"
        >
          <Eye className="w-4 h-4" />
          查看
        </Button>
      </div>
    </Card>
  );
}
