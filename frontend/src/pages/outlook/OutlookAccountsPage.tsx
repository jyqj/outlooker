import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw, Shield, UserRound } from 'lucide-react';

import api, { clearAuthTokens } from '@/lib/api';
import { batchRefreshOutlookTokens } from '@/lib/api/outlook-accounts-api';
import { useDebounce, useOutlookAccountsQuery } from '@/lib/hooks';
import { queryKeys } from '@/lib/queryKeys';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

export default function OutlookAccountsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [accountType, setAccountType] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const debouncedStatus = useDebounce(status.trim(), 250);
  const debouncedAccountType = useDebounce(accountType.trim(), 250);
  const { data, isLoading, isFetching, refetch } = useOutlookAccountsQuery({
    status: debouncedStatus,
    accountType: debouncedAccountType,
    limit,
    offset,
  });
  const accounts = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const [batchRefreshing, setBatchRefreshing] = useState(false);

  const handleLogout = async () => {
    try {
      await api.post('/api/admin/logout', {});
    } finally {
      clearAuthTokens();
      navigate('/admin/login');
    }
  };

  const invalidateVisibleAssets = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.outlookAccountsBase() }),
      ...accounts.map((item) =>
        queryClient.invalidateQueries({
          queryKey: queryKeys.outlookAccountDetail(item.email),
        })
      ),
    ]);
  };

  const handleBatchRefresh = async () => {
    setBatchRefreshing(true);
    try {
      await batchRefreshOutlookTokens({ emails: accounts.map((item) => item.email) });
      await invalidateVisibleAssets();
    } finally {
      setBatchRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Outlook 账户</h2>
            <p className="text-sm text-muted-foreground">查看 Token、能力位和账户资产状态。</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate('/admin')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回后台
            </Button>
            <Button onClick={() => void refetch()} disabled={isFetching}>
              <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
              {isFetching ? '刷新中...' : '刷新'}
            </Button>
            <Button
              onClick={handleBatchRefresh}
              disabled={batchRefreshing || isFetching || accounts.length === 0}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${batchRefreshing ? 'animate-spin' : ''}`} />
              {batchRefreshing ? '批量刷新中...' : '批量刷新 Token'}
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>筛选与分页</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-4">
            <div className="w-48 space-y-2">
              <div className="text-sm text-muted-foreground">状态</div>
              <Input
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setOffset(0);
                }}
                placeholder="active / suspended"
              />
            </div>
            <div className="w-48 space-y-2">
              <div className="text-sm text-muted-foreground">类型</div>
              <Input
                value={accountType}
                onChange={(event) => {
                  setAccountType(event.target.value);
                  setOffset(0);
                }}
                placeholder="consumer / org"
              />
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
              >
                下一页
              </Button>
              <Badge variant="outline">
                {Math.floor(offset / limit) + 1} / {Math.max(1, Math.ceil(total / limit))}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="w-5 h-5" />
              账户资产列表
              {!isLoading && isFetching && (
                <span className="text-xs font-normal text-muted-foreground">同步中</span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">正在加载 Outlook 账户...</p>
            ) : accounts.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无 Outlook 账户资产。</p>
            ) : (
              accounts.map((account) => (
                <div
                  key={account.email}
                  className="border rounded-xl p-4 flex items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="font-medium">{account.email}</div>
                    <div className="text-sm text-muted-foreground">
                      类型: {account.account_type} · 状态: {account.status}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={account.capabilities?.graph_ready ? 'default' : 'secondary'}>
                        <Shield className="w-3 h-3 mr-1" />
                        Graph {account.capabilities?.graph_ready ? 'Ready' : 'Off'}
                      </Badge>
                      <Badge variant="outline">Token: {account.token?.status ?? 'none'}</Badge>
                      <Badge variant={account.token?.has_refresh_token ? 'success' : 'warning'}>
                        Refresh {account.token?.has_refresh_token ? 'Ready' : 'Missing'}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => navigate(`/admin/outlook/accounts/${encodeURIComponent(account.email)}`)}
                  >
                    查看详情
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
