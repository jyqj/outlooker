import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MailPlus, RefreshCw } from 'lucide-react';

import api, { clearAuthTokens } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

export default function AuxEmailPoolPage() {
  const navigate = useNavigate();
  const [resources, setResources] = useState<Array<Record<string, unknown>>>([]);
  const [status, setStatus] = useState('');
  const [importText, setImportText] = useState('');

  const loadResources = async () => {
    const res = await api.get('/api/outlook/resources/aux-emails', {
      params: status ? { status } : undefined,
    });
    setResources(res.data?.data?.items ?? []);
  };

  const handleLogout = async () => {
    try {
      await api.post('/api/admin/logout', {});
    } finally {
      clearAuthTokens();
      navigate('/admin/login');
    }
  };

  useEffect(() => {
    void loadResources();
  }, [status]);

  const handleImport = async () => {
    const items = importText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((address) => ({ address }));
    await api.post('/api/outlook/resources/aux-emails/import', { items });
    setImportText('');
    await loadResources();
  };

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">辅助邮箱资源池</h2>
            <p className="text-sm text-muted-foreground">查看可用、隔离、轮转中的辅助邮箱资源。</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate('/admin')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回后台
            </Button>
            <Button onClick={() => loadResources()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              刷新
            </Button>
          </div>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MailPlus className="w-5 h-5" />
              资源池概览
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 items-end">
              <div className="w-52 space-y-2">
                <div className="text-sm text-muted-foreground">状态筛选</div>
                <Input value={status} onChange={(e) => setStatus(e.target.value)} placeholder="available / bound / quarantine" />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-3">
                {resources.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无辅助邮箱资源。</p>
                ) : (
                  resources.map((resource) => (
                    <div key={String(resource.id)} className="rounded-xl border p-4 flex items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="font-medium">{String(resource.address)}</div>
                        <div className="text-sm text-muted-foreground">
                          状态: {String(resource.status)} · 渠道: {String(resource.channel_id ?? 'N/A')} · fail_count: {String(resource.fail_count ?? 0)}
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        onClick={async () => {
                          await api.post(`/api/outlook/resources/aux-emails/${String(resource.id)}/rotate`, {
                            reason: 'manual_ui_rotate',
                          });
                          await loadResources();
                        }}
                      >
                        手动轮转
                      </Button>
                    </div>
                  ))
                )}
              </div>

              <div className="space-y-3">
                <div className="text-sm text-muted-foreground">批量导入（每行一个邮箱）</div>
                <Textarea rows={14} value={importText} onChange={(e) => setImportText(e.target.value)} />
                <Button onClick={handleImport}>导入资源</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
