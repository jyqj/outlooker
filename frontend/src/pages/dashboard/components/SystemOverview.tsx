import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Settings2, Users, RefreshCw, Mail } from 'lucide-react';
import api from '@/lib/api';
import { MESSAGES } from '@/lib/constants';
import { queryKeys } from '@/lib/queryKeys';
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

  const accountsCount = metricsData?.data?.email_manager?.accounts_count || 0;
  const cachedEmails = metricsData?.data?.email_manager?.email_cache?.total_messages || 0;

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
          onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.systemConfig() }),
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
            queryClient.invalidateQueries({ queryKey: queryKeys.systemMetrics() });
            queryClient.invalidateQueries({ queryKey: queryKeys.accounts() });
          },
        },
      );
    } finally {
      setRefreshingCache(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Accounts Count Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">账户总数</CardTitle>
          <Users className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{accountsCount}</div>
          <p className="text-xs text-muted-foreground mt-1">已导入的邮箱账户</p>
        </CardContent>
      </Card>

      {/* Cached Emails Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">缓存邮件</CardTitle>
          <Mail className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold">{cachedEmails}</div>
              <p className="text-xs text-muted-foreground mt-1">已缓存的邮件数量</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCacheRefresh}
              disabled={refreshingCache}
              className="h-8 text-xs gap-1"
            >
              <RefreshCw className={`w-3 h-3 ${refreshingCache ? 'animate-spin' : ''}`} />
              {refreshingCache ? '清理中' : '清理'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Email Limit Config Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">邮件获取限制</CardTitle>
          <Settings2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={1}
              max={50}
              value={emailLimit}
              onChange={(e) => setEmailLimit(e.target.value)}
              className="w-20 text-center font-bold"
            />
            <span className="text-sm text-muted-foreground">封/次</span>
            <Button
              size="sm"
              onClick={handleConfigSave}
              disabled={savingConfig}
              className="ml-auto"
            >
              {savingConfig ? '...' : '保存'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {metricsData?.data?.warning && (
        <div className="md:col-span-3 rounded-md bg-yellow-500/10 p-3 text-sm text-yellow-900 dark:text-yellow-200 border border-yellow-500/30">
          {metricsData.data.warning}
        </div>
      )}
    </div>
  );
}
