import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Users, Tags, Activity, Settings2, AlertTriangle, Shield, ShieldCheck, ShieldX, Clock } from 'lucide-react';
import api from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { ApiResponse, DashboardSummary } from '@/types';

function useDashboardSummary() {
  return useQuery({
    queryKey: queryKeys.dashboardSummary(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<DashboardSummary>>('/api/dashboard/summary');
      return res.data;
    },
    refetchInterval: 60_000,
  });
}

export function SystemOverview() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data } = useDashboardSummary();
  const summary = data?.data;

  const health = summary?.health || {};
  const total = health.total || 0;
  const healthy = health.healthy || 0;
  const unhealthy = (health.token_expired || 0) + (health.token_invalid || 0) + (health.error || 0);
  const unknown = health.unknown || 0;

  const tagStats = summary?.tags;
  const totalTags = tagStats?.tags?.length || 0;
  const taggedAccounts = tagStats?.tagged_accounts || 0;
  const untaggedAccounts = tagStats?.untagged_accounts || 0;
  const taggedPercent = total > 0 ? Math.round((taggedAccounts / total) * 100) : 0;

  const alerts = summary?.alerts || [];
  const recentEvents = summary?.recent_events || [];

  return (
    <div className="space-y-4">
      {/* Row 1: Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Account Overview */}
        <Card className="hover:border-primary/20 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t('dashboard.overview.totalAccounts')}
            </CardTitle>
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Users className="h-4 w-4 text-primary" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold tracking-tight">{total}</div>
            {total > 0 && unknown < total && (
              <div className="flex items-center gap-3 mt-2 text-xs">
                <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                  <ShieldCheck className="w-3 h-3" /> {healthy}
                </span>
                {unhealthy > 0 && (
                  <span className="flex items-center gap-1 text-red-500">
                    <ShieldX className="w-3 h-3" /> {unhealthy}
                  </span>
                )}
                {unknown > 0 && (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Shield className="w-3 h-3" /> {unknown}
                  </span>
                )}
              </div>
            )}
            {unknown === total && total > 0 && (
              <p className="text-xs text-muted-foreground mt-1">{t('dashboard.overview.totalAccountsSub')}</p>
            )}
          </CardContent>
        </Card>

        {/* Tag Distribution */}
        <Card className="hover:border-primary/20 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t('dashboard.overview.tagDistribution')}
            </CardTitle>
            <div className="p-1.5 rounded-lg bg-info/10">
              <Tags className="h-4 w-4 text-info" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight">{totalTags}</span>
              <span className="text-sm text-muted-foreground">{t('dashboard.overview.tagCount')}</span>
            </div>
            {total > 0 && (
              <div className="mt-2 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{t('dashboard.overview.tagged')}: {taggedAccounts}</span>
                  <span className="text-muted-foreground">{t('dashboard.overview.untagged')}: {untaggedAccounts}</span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${taggedPercent}%` }} />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* System Status */}
        <Card className="hover:border-primary/20 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t('dashboard.overview.systemStatus')}
            </CardTitle>
            <div className="p-1.5 rounded-lg bg-success/10">
              <Activity className="h-4 w-4 text-success" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-medium">{t('dashboard.overview.running')}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/settings')}
              className="w-full gap-1.5 text-xs"
            >
              <Settings2 className="w-3 h-3" />
              {t('dashboard.overview.goSettings')}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Alerts + Recent Activity */}
      {(alerts.length > 0 || recentEvents.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Alerts */}
          {alerts.length > 0 && (
            <Card className="border-warning/30">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <AlertTriangle className="w-4 h-4 text-warning" />
                  {t('dashboard.overview.alerts')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {alerts.map((alert, i) => (
                  <div
                    key={i}
                    className={`flex items-center justify-between text-sm rounded-md px-3 py-2 ${
                      alert.level === 'error'
                        ? 'bg-destructive/10 text-destructive'
                        : 'bg-warning/10 text-warning'
                    }`}
                  >
                    <span>{alert.message}</span>
                    <span className="font-bold">{alert.count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Recent Activity */}
          {recentEvents.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                  {t('dashboard.overview.recentActivity')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {recentEvents.slice(0, 5).map((evt, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground truncate max-w-[60%]">
                        {evt.action || evt.event_type}
                        {evt.resource && ` · ${evt.resource}`}
                      </span>
                      <span className="text-muted-foreground shrink-0">
                        {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
