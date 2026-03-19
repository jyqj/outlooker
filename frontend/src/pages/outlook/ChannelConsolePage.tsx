import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, SplitSquareVertical } from 'lucide-react';

import api, { clearAuthTokens } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

export default function ChannelConsolePage() {
  const navigate = useNavigate();
  const [channels, setChannels] = useState<Array<Record<string, unknown>>>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<number | null>(null);
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [createCode, setCreateCode] = useState('');
  const [createName, setCreateName] = useState('');
  const [bindEmails, setBindEmails] = useState('');
  const [bindResourceIds, setBindResourceIds] = useState('');

  const loadChannels = async () => {
    const res = await api.get('/api/outlook/channels');
    const items = res.data?.data?.items ?? [];
    setChannels(items);
    if (!selectedChannelId && items.length > 0) {
      setSelectedChannelId(Number(items[0].id));
    }
  };

  const loadStats = async (channelId: number) => {
    const res = await api.get('/api/outlook/channels/stats', { params: { channel_id: channelId } });
    setStats(res.data?.data ?? {});
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
    void loadChannels();
  }, []);

  useEffect(() => {
    if (selectedChannelId) {
      void loadStats(selectedChannelId);
    }
  }, [selectedChannelId]);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">渠道控制台</h2>
            <p className="text-sm text-muted-foreground">按渠道查看账户分配、资源隔离和运行统计。</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate('/admin')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回后台
            </Button>
            <Button onClick={() => loadChannels()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              刷新
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SplitSquareVertical className="w-5 h-5" />
                渠道列表
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {channels.length === 0 ? (
                <p className="text-sm text-muted-foreground">暂无渠道。</p>
              ) : (
                channels.map((channel) => (
                  <div
                    key={String(channel.id)}
                    className={`rounded-xl border p-4 cursor-pointer ${selectedChannelId === Number(channel.id) ? 'border-primary' : ''}`}
                    onClick={() => setSelectedChannelId(Number(channel.id))}
                  >
                    <div className="font-medium">{String(channel.name)}</div>
                    <div className="text-sm text-muted-foreground">
                      code: {String(channel.code)} · 状态: {String(channel.status)} · priority: {String(channel.priority)}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>渠道统计</CardTitle></CardHeader>
            <CardContent>
              <Textarea rows={14} readOnly value={JSON.stringify(stats, null, 2)} />
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader><CardTitle>创建渠道</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder="code" value={createCode} onChange={(e) => setCreateCode(e.target.value)} />
              <Input placeholder="name" value={createName} onChange={(e) => setCreateName(e.target.value)} />
              <Button
                onClick={async () => {
                  await api.post('/api/outlook/channels', { code: createCode, name: createName });
                  setCreateCode('');
                  setCreateName('');
                  await loadChannels();
                }}
              >
                创建渠道
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>绑定账户</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea rows={8} value={bindEmails} onChange={(e) => setBindEmails(e.target.value)} placeholder="每行一个 Outlook 账户邮箱" />
              <Button
                disabled={!selectedChannelId}
                onClick={async () => {
                  const emails = bindEmails.split('\n').map((item) => item.trim()).filter(Boolean);
                  await api.post(`/api/outlook/channels/${selectedChannelId}/accounts/bind`, { emails });
                  setBindEmails('');
                  if (selectedChannelId) {
                    await loadStats(selectedChannelId);
                  }
                }}
              >
                绑定到账户池
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>绑定资源</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea rows={8} value={bindResourceIds} onChange={(e) => setBindResourceIds(e.target.value)} placeholder="每行一个资源 ID" />
              <Button
                disabled={!selectedChannelId}
                onClick={async () => {
                  const resourceIds = bindResourceIds
                    .split('\n')
                    .map((item) => Number(item.trim()))
                    .filter((value) => !Number.isNaN(value));
                  await api.post(`/api/outlook/channels/${selectedChannelId}/resources/bind`, { resource_ids: resourceIds });
                  setBindResourceIds('');
                  if (selectedChannelId) {
                    await loadStats(selectedChannelId);
                  }
                }}
              >
                绑定资源
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
