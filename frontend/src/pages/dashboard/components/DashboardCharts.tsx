import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { ApiResponse } from '@/types';

interface DashboardSummary {
  health: Record<string, number>;
  tags: { tags: { name: string; count: number }[] };
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: '#22c55e',
  token_expired: '#f59e0b',
  token_invalid: '#ef4444',
  error: '#ef4444',
  unknown: '#94a3b8',
};

export function DashboardCharts() {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: queryKeys.dashboardSummary(),
    queryFn: async () => {
      const res = await api.get<ApiResponse<DashboardSummary>>('/api/dashboard/summary');
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const health = data?.data?.health || {};
  const tagsList = data?.data?.tags?.tags || [];

  const healthData = Object.entries(health)
    .filter(([k]) => k !== 'total')
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0);

  const tagData = tagsList.slice(0, 10).map((t) => ({ name: t.name, count: t.count }));

  const hasHealthData = healthData.length > 0;
  const hasTagData = tagData.length > 0;

  if (!hasHealthData && !hasTagData) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {hasHealthData && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t('dashboard.charts.healthDistribution')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={healthData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={2}>
                  {healthData.map((entry) => (
                    <Cell key={entry.name} fill={HEALTH_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [String(value), t(`dashboard.charts.${name}`, String(name))]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-3 justify-center mt-2">
              {healthData.map((d) => (
                <div key={d.name} className="flex items-center gap-1.5 text-xs">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: HEALTH_COLORS[d.name] || '#94a3b8' }} />
                  <span className="text-muted-foreground">{t(`dashboard.charts.${d.name}`, d.name)}</span>
                  <span className="font-medium">{d.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {hasTagData && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t('dashboard.charts.tagDistribution')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={tagData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
