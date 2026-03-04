import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, FileText, ChevronLeft, ChevronRight } from 'lucide-react';
import api, { clearAuthTokens } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';
import type { ApiResponse } from '@/types';

interface AuditEvent {
  id: number;
  event_type: string;
  timestamp: string;
  user_id?: string;
  ip_address?: string;
  action?: string;
  resource?: string;
  success: number;
  error_message?: string;
  details?: Record<string, unknown>;
}

const PAGE_SIZE = 20;

export default function AuditPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ['audit-events', typeFilter, page],
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
      if (typeFilter) params.event_type = typeFilter;
      const res = await api.get<ApiResponse<{ events: AuditEvent[] }>>('/api/audit/events', { params });
      return res.data;
    },
  });

  const events = data?.data?.events || [];

  const handleLogout = useCallback(async () => {
    try { await api.post('/api/admin/logout', {}); } catch { /* ignore */ }
    clearAuthTokens();
    navigate('/admin/login');
  }, [navigate]);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin')} className="gap-1.5">
            <ArrowLeft className="w-4 h-4" /> {t('common.back')}
          </Button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{t('audit.title')}</h2>
            <p className="text-sm text-muted-foreground">{t('audit.subtitle')}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <Input
            placeholder={t('audit.filterPlaceholder')}
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}
            className="max-w-xs"
          />
        </div>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FileText className="w-4 h-4" /> {t('audit.events')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-sm text-muted-foreground py-8 text-center">{t('common.loading')}</p>
            ) : events.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">{t('audit.noEvents')}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 pr-4 font-medium">{t('audit.time')}</th>
                      <th className="pb-2 pr-4 font-medium">{t('audit.type')}</th>
                      <th className="pb-2 pr-4 font-medium">{t('audit.action')}</th>
                      <th className="pb-2 pr-4 font-medium">{t('audit.ip')}</th>
                      <th className="pb-2 font-medium">{t('audit.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((evt) => (
                      <tr key={evt.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                          {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : '-'}
                        </td>
                        <td className="py-2 pr-4">
                          <span className="px-1.5 py-0.5 rounded text-xs bg-muted">{evt.event_type}</span>
                        </td>
                        <td className="py-2 pr-4 text-xs">{evt.action || evt.resource || '-'}</td>
                        <td className="py-2 pr-4 text-xs text-muted-foreground">{evt.ip_address || '-'}</td>
                        <td className="py-2">
                          <span className={`text-xs font-medium ${evt.success ? 'text-green-600' : 'text-red-500'}`}>
                            {evt.success ? '✓' : '✗'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex items-center justify-between mt-4 pt-3 border-t">
              <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-xs text-muted-foreground">{t('audit.page', { page: page + 1 })}</span>
              <Button variant="ghost" size="sm" disabled={events.length < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
