import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Settings2, Activity, RefreshCw } from 'lucide-react';
import api from '@/lib/api';
import { MESSAGES } from '@/lib/constants';
import { useSystemConfigQuery, useSystemMetricsQuery, useApiAction } from '@/lib/hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export function SystemOverview() {
  const queryClient = useQueryClient();
  const { data: configData } = useSystemConfigQuery();
  const { data: metricsData } = useSystemMetricsQuery();
  const apiAction = useApiAction();

  const [emailLimit, setEmailLimit] = useState<number | string>(5);
  const [savingConfig, setSavingConfig] = useState(false);
  const [refreshingCache, setRefreshingCache] = useState(false);

  const cacheHitRate = metricsData?.data?.email_manager?.cache_hit_rate;

  useEffect(() => {
    if (configData?.data?.email_limit) {
      setEmailLimit(configData.data.email_limit);
    }
  }, [configData]);

  const handleConfigSave = async () => {
    setSavingConfig(true);
    try {
      await apiAction(
        () => api.post('/api/system/config', { email_limit: Number(emailLimit) }),
        {
          successMessage: MESSAGES.SUCCESS_CONFIG_UPDATED,
          errorMessage: MESSAGES.ERROR_CONFIG_UPDATE_FAILED,
          onSuccess: () => queryClient.invalidateQueries({ queryKey: ['system-config'] }),
        },
      );
    } finally {
      setSavingConfig(false);
    }
  };

  const handleCacheRefresh = async () => {
    setRefreshingCache(true);
    try {
      await apiAction(
        () => api.post('/api/system/cache/refresh'),
        {
          successMessage: MESSAGES.SUCCESS_CACHE_REFRESHED,
          errorMessage: MESSAGES.ERROR_CACHE_REFRESH_FAILED,
          onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['system-metrics'] });
            queryClient.invalidateQueries({ queryKey: ['accounts'] });
          },
        },
      );
    } finally {
      setRefreshingCache(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Email Limit Config Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-base font-medium">邮件获取限制</CardTitle>
          <Settings2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="text-2xl font-bold">每次最多 {emailLimit} 封</div>
            <div className="flex gap-3">
              <Input
                type="number"
                min={1}
                max={50}
                value={emailLimit}
                onChange={(e) => setEmailLimit(e.target.value)}
                className="flex-1"
              />
              <Button
                onClick={handleConfigSave}
                disabled={savingConfig}
              >
                {savingConfig ? '保存中...' : '保存'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Metrics Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-base font-medium">系统指标</CardTitle>
          <Activity className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="flex justify-between items-center mb-4">
            <div className="text-2xl font-bold">
              {metricsData?.data?.email_manager?.accounts_count || 0} 个账户
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCacheRefresh}
              disabled={refreshingCache}
              className="h-8 text-xs gap-1"
            >
              <RefreshCw className={`w-3 h-3 ${refreshingCache ? 'animate-spin' : ''}`} />
              {refreshingCache ? '刷新中...' : '刷新缓存'}
            </Button>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">缓存命中</dt>
              <dd className="font-semibold">{metricsData?.data?.email_manager?.cache_hits ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">缓存未命中</dt>
              <dd className="font-semibold">{metricsData?.data?.email_manager?.cache_misses ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">IMAP 复用</dt>
              <dd className="font-semibold">{metricsData?.data?.email_manager?.client_reuses ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">IMAP 创建</dt>
              <dd className="font-semibold">{metricsData?.data?.email_manager?.client_creates ?? 0}</dd>
            </div>
            <div className="flex justify-between col-span-2 pt-2 border-t">
              <dt className="text-muted-foreground">缓存命中率</dt>
              <dd className="font-bold text-green-600">
                {typeof cacheHitRate === 'number'
                  ? `${(cacheHitRate * 100).toFixed(1)}%`
                  : '--'}
              </dd>
            </div>
          </dl>

          {metricsData?.data?.warning && (
            <div className="mt-3 rounded-md bg-yellow-500/10 p-3 text-sm text-yellow-900 dark:text-yellow-200 border border-yellow-500/30">
              {metricsData.data.warning}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
