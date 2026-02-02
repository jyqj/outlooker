import { Package, CheckCircle, XCircle } from 'lucide-react';
import { StatsCard } from '@/components/ui/StatsCard';
import type { TagsStatsProps } from './types';

export function TagsStatsSection({ 
  totalAccounts, 
  taggedAccounts, 
  untaggedAccounts 
}: TagsStatsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatsCard
        title="总账户数"
        value={totalAccounts}
        icon={<Package className="w-5 h-5" />}
        color="primary"
      />
      <StatsCard
        title="已标记账户"
        value={taggedAccounts}
        icon={<CheckCircle className="w-5 h-5" />}
        color="success"
      />
      <StatsCard
        title="未标记账户"
        value={untaggedAccounts}
        icon={<XCircle className="w-5 h-5" />}
        color="warning"
      />
    </div>
  );
}
