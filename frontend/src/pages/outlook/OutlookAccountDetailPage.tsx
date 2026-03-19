import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, KeyRound, RefreshCw, ShieldAlert, ShieldCheck, UserRound } from 'lucide-react';

import api, { clearAuthTokens } from '@/lib/api';
import {
  changeOutlookPassword,
  dismissOutlookRisk,
  getOutlookRiskyUsers,
  refreshOutlookToken,
  revokeOutlookSessions,
  updateOutlookMailboxSettings,
  updateOutlookProfile,
  updateOutlookRegionalSettings,
} from '@/lib/api/outlook-accounts-api';
import {
  useOutlookAccountDetailQuery,
  useOutlookAuthMethodsQuery,
  useOutlookMailboxSettingsQuery,
  useOutlookProfileQuery,
  useOutlookRegionalSettingsQuery,
} from '@/lib/hooks';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { AuthMethodsPanel } from '@/components/outlook/auth-methods/AuthMethodsPanel';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

function stringify(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export default function OutlookAccountDetailPage() {
  const { email = '' } = useParams();
  const decodedEmail = decodeURIComponent(email);
  const navigate = useNavigate();

  const detailQuery = useOutlookAccountDetailQuery(decodedEmail, !!decodedEmail);
  const profileQuery = useOutlookProfileQuery(decodedEmail, false, !!decodedEmail);
  const authMethodsQuery = useOutlookAuthMethodsQuery(decodedEmail, !!decodedEmail);
  const mailboxQuery = useOutlookMailboxSettingsQuery(decodedEmail, !!decodedEmail);
  const regionalQuery = useOutlookRegionalSettingsQuery(decodedEmail, !!decodedEmail);

  const [profileEditor, setProfileEditor] = useState('{}');
  const [mailboxEditor, setMailboxEditor] = useState('{}');
  const [regionalEditor, setRegionalEditor] = useState('{}');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [riskyUsers, setRiskyUsers] = useState<string>('{}');
  const [dismissUserId, setDismissUserId] = useState('');

  useEffect(() => {
    if (profileQuery.data?.data) {
      setProfileEditor(stringify(profileQuery.data.data));
    }
  }, [profileQuery.data]);

  useEffect(() => {
    if (mailboxQuery.data?.data) {
      setMailboxEditor(stringify(mailboxQuery.data.data));
    }
  }, [mailboxQuery.data]);

  useEffect(() => {
    if (regionalQuery.data?.data) {
      setRegionalEditor(stringify(regionalQuery.data.data));
    }
  }, [regionalQuery.data]);

  const handleLogout = async () => {
    try {
      await api.post('/api/admin/logout', {});
    } finally {
      clearAuthTokens();
      navigate('/admin/login');
    }
  };

  const parseEditor = (value: string) => JSON.parse(value || '{}') as Record<string, unknown>;

  const account = detailQuery.data?.data;
  const authBundle = authMethodsQuery.data?.data ?? {};

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">账户详情</h2>
            <p className="text-sm text-muted-foreground">{decodedEmail}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate('/admin/outlook/accounts')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回账户列表
            </Button>
            <Button onClick={() => refreshOutlookToken(decodedEmail)}>
              <RefreshCw className="w-4 h-4 mr-2" />
              刷新 Token
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="w-5 h-5" />
              账户概览
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {detailQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">正在加载账户详情...</p>
            ) : !account ? (
              <p className="text-sm text-muted-foreground">未找到该 Outlook 账户。</p>
            ) : (
              <>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">状态: {account.status}</Badge>
                  <Badge variant="outline">类型: {account.account_type}</Badge>
                  <Badge variant={account.capabilities?.graph_ready ? 'default' : 'secondary'}>
                    Graph: {account.capabilities?.graph_ready ? 'Ready' : 'Off'}
                  </Badge>
                  <Badge variant="outline">Token: {account.token?.status ?? 'none'}</Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  最近同步: {account.last_synced_at || 'N/A'} · 来源账户: {account.source_account_email || 'N/A'}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader><CardTitle>用户资料</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea rows={12} value={profileEditor} onChange={(e) => setProfileEditor(e.target.value)} />
              <Button onClick={() => updateOutlookProfile(decodedEmail, parseEditor(profileEditor))}>保存资料</Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>身份验证方式</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <AuthMethodsPanel data={authBundle as Record<string, unknown>} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>邮箱设置</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea rows={12} value={mailboxEditor} onChange={(e) => setMailboxEditor(e.target.value)} />
              <Button onClick={() => updateOutlookMailboxSettings(decodedEmail, parseEditor(mailboxEditor))}>
                保存邮箱设置
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>区域设置</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea rows={12} value={regionalEditor} onChange={(e) => setRegionalEditor(e.target.value)} />
              <Button onClick={() => updateOutlookRegionalSettings(decodedEmail, parseEditor(regionalEditor))}>
                保存区域设置
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="w-5 h-5" />
                密码修改
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input type="password" placeholder="当前密码" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
              <Input type="password" placeholder="新密码" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              <Button onClick={() => changeOutlookPassword(decodedEmail, currentPassword, newPassword)}>
                修改密码
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5" />
                会话与风险处理
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button onClick={() => revokeOutlookSessions(decodedEmail)}>撤销所有会话</Button>
              <Button
                variant="outline"
                onClick={async () => {
                  const result = await getOutlookRiskyUsers(decodedEmail);
                  setRiskyUsers(stringify(result.data));
                }}
              >
                <ShieldAlert className="w-4 h-4 mr-2" />
                查看风险用户
              </Button>
              <Textarea rows={8} readOnly value={riskyUsers} />
              <Input placeholder="输入 user_id 解除风险" value={dismissUserId} onChange={(e) => setDismissUserId(e.target.value)} />
              <Button variant="outline" onClick={() => dismissOutlookRisk(decodedEmail, dismissUserId)}>
                解除风险
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
