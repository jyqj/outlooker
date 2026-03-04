import { useTranslation } from 'react-i18next';
import { XCircle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import type { UntaggedAccountsCardProps } from './types';

export function UntaggedAccountsCard({ count, onView }: UntaggedAccountsCardProps) {
  const { t } = useTranslation();
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
            <p className="font-medium">{t('tags.untaggedMessage', { count })}</p>
            <p className="text-sm text-muted-foreground">
              {t('tags.untaggedHint')}
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
          {t('tags.viewUntagged')}
        </Button>
      </div>
    </Card>
  );
}
