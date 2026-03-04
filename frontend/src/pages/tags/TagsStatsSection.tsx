import { useTranslation } from 'react-i18next';
import { Package, CheckCircle, XCircle } from 'lucide-react';
import { StatsCard } from '@/components/ui/StatsCard';
import type { TagsStatsProps } from './types';

export function TagsStatsSection({ 
  totalAccounts, 
  taggedAccounts, 
  untaggedAccounts 
}: TagsStatsProps) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatsCard
        title={t('tags.stats.total')}
        value={totalAccounts}
        icon={<Package className="w-5 h-5" />}
        color="primary"
      />
      <StatsCard
        title={t('tags.stats.tagged')}
        value={taggedAccounts}
        icon={<CheckCircle className="w-5 h-5" />}
        color="success"
      />
      <StatsCard
        title={t('tags.stats.untagged')}
        value={untaggedAccounts}
        icon={<XCircle className="w-5 h-5" />}
        color="warning"
      />
    </div>
  );
}
