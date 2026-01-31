import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  Tags, 
  ArrowLeft, 
  Shuffle, 
  Users, 
  Eye,
  RefreshCw,
  Plus,
  Package,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import api from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type { ApiResponse } from '@/types';
import PickAccountModal from '@/components/PickAccountModal';

// Types
interface TagStatItem {
  name: string;
  count: number;
  percentage: number;
}

interface TagStats {
  total_accounts: number;
  tagged_accounts: number;
  untagged_accounts: number;
  tags: TagStatItem[];
}

// Query hook for tag statistics
function useTagStatsQuery() {
  return useQuery({
    queryKey: queryKeys.tagStats(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<TagStats>>('/api/accounts/tags/stats');
      return res.data;
    },
  });
}

// Statistics Card Component
function StatsCard({ 
  title, 
  value, 
  icon: Icon, 
  color = 'primary' 
}: { 
  title: string; 
  value: number | string; 
  icon: React.ElementType;
  color?: 'primary' | 'success' | 'warning' | 'muted';
}) {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-500/10 text-green-600 dark:text-green-400',
    warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    muted: 'bg-muted text-muted-foreground',
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </Card>
  );
}

// Tag List Item Component
function TagListItem({ 
  tag, 
  onPick, 
  onView,
  isLoading 
}: { 
  tag: TagStatItem;
  onPick: (tagName: string) => void;
  onView: (tagName: string) => void;
  isLoading: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-4 border-b last:border-b-0 hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="px-3 py-1">
          {tag.name}
        </Badge>
        <span className="text-sm text-muted-foreground">
          {tag.count} 个账户 ({tag.percentage}%)
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPick(tag.name)}
          disabled={isLoading}
          className="gap-1"
        >
          <Shuffle className="w-3.5 h-3.5" />
          取号
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(tag.name)}
          className="gap-1"
        >
          <Eye className="w-3.5 h-3.5" />
          查看
        </Button>
      </div>
    </div>
  );
}

// Loading Skeleton
function TagsPageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="p-4">
            <div className="flex items-center gap-3">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="w-20 h-4" />
                <Skeleton className="w-12 h-6" />
              </div>
            </div>
          </Card>
        ))}
      </div>
      <Card className="divide-y">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Skeleton className="w-24 h-6 rounded-full" />
              <Skeleton className="w-32 h-4" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="w-16 h-8" />
              <Skeleton className="w-16 h-8" />
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

// Main Page Component
export default function TagsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useTagStatsQuery();
  
  // Pick account modal state
  const [pickModal, setPickModal] = useState<{
    isOpen: boolean;
    preselectedTag: string;
  }>({ isOpen: false, preselectedTag: '' });

  const stats = data?.data;

  const handlePick = (tagName: string) => {
    setPickModal({ isOpen: true, preselectedTag: tagName });
  };

  const handleView = (tagName: string) => {
    // Navigate to dashboard with tag filter (could be implemented later)
    // For now, show the accounts in the dashboard
    navigate(`/admin?tag=${encodeURIComponent(tagName)}`);
  };

  const handleRefresh = () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: queryKeys.tagStats() });
  };

  const handlePickSuccess = () => {
    // Refresh stats after successful pick
    refetch();
  };

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-background/80 border-b px-6 py-4 flex justify-between items-center sticky top-0 z-20 shadow-md backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/admin')}
            className="gap-1"
          >
            <ArrowLeft className="w-4 h-4" />
            返回
          </Button>
          <div className="h-6 w-px bg-border" />
          <div className="bg-primary p-2 rounded-lg text-primary-foreground">
            <Tags className="w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">标签管理</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => setPickModal({ isOpen: true, preselectedTag: '' })}
            className="gap-1"
          >
            <Plus className="w-4 h-4" />
            随机取号
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
        {isLoading ? (
          <TagsPageSkeleton />
        ) : isError ? (
          <Card className="p-6 text-center">
            <p className="text-destructive mb-4">加载标签统计失败</p>
            <Button variant="outline" onClick={() => refetch()}>
              重试
            </Button>
          </Card>
        ) : stats ? (
          <>
            {/* Statistics Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatsCard
                title="总账户数"
                value={stats.total_accounts}
                icon={Package}
                color="primary"
              />
              <StatsCard
                title="已标记账户"
                value={stats.tagged_accounts}
                icon={CheckCircle}
                color="success"
              />
              <StatsCard
                title="未标记账户"
                value={stats.untagged_accounts}
                icon={XCircle}
                color="warning"
              />
            </div>

            {/* Tags List */}
            <Card>
              <div className="p-4 border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-muted-foreground" />
                  <h2 className="font-semibold">标签列表</h2>
                  <Badge variant="outline">{stats.tags.length} 个标签</Badge>
                </div>
              </div>
              
              {stats.tags.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Tags className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>暂无标签</p>
                  <p className="text-sm mt-1">在账户管理中为账户添加标签后，这里会显示统计信息</p>
                </div>
              ) : (
                <div>
                  {stats.tags.map((tag) => (
                    <TagListItem
                      key={tag.name}
                      tag={tag}
                      onPick={handlePick}
                      onView={handleView}
                      isLoading={isLoading}
                    />
                  ))}
                </div>
              )}
            </Card>

            {/* Quick Actions for Untagged Accounts */}
            {stats.untagged_accounts > 0 && (
              <Card className="p-4 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-amber-500/20 text-amber-600 dark:text-amber-400">
                      <XCircle className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium">有 {stats.untagged_accounts} 个账户尚未标记</p>
                      <p className="text-sm text-muted-foreground">
                        这些账户可以被任何标签的取号操作选中
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/admin?untagged=true')}
                    className="gap-1"
                  >
                    <Eye className="w-4 h-4" />
                    查看
                  </Button>
                </div>
              </Card>
            )}
          </>
        ) : null}
      </main>

      {/* Pick Account Modal */}
      <PickAccountModal
        isOpen={pickModal.isOpen}
        preselectedTag={pickModal.preselectedTag}
        availableTags={stats?.tags.map(t => t.name) || []}
        onClose={() => setPickModal({ isOpen: false, preselectedTag: '' })}
        onSuccess={handlePickSuccess}
      />
    </div>
  );
}
