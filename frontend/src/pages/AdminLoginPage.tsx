import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User, Inbox, Loader2 } from 'lucide-react';
import api, { setAuthTokens } from '@/lib/api';
import { handleApiError } from '@/lib/error';
import { MESSAGES } from '@/lib/constants';
import { useAsyncTask } from '@/lib/hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { AdminLoginResponse } from '@/types/models';

export default function AdminLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { loading, run } = useAsyncTask();
  const navigate = useNavigate();

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await run(async () => {
        const response = await api.post<AdminLoginResponse>('/api/admin/login', {
          username,
          password,
        });

        const data = response.data;
        if (data.access_token) {
          setAuthTokens({
            accessToken: data.access_token,
            expiresIn: data.expires_in,
          });
          navigate('/admin');
        } else {
          setError('登录响应格式错误');
        }
      });
    } catch (err) {
      handleApiError(err, '登录失败');
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || MESSAGES.ERROR_LOGIN_FAILED);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/60 p-4">
      <div className="w-full max-w-md">
        {/* Logo Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="bg-primary p-3 rounded-lg text-primary-foreground">
              <Inbox className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Outlooker</h1>
          </div>
          <p className="text-muted-foreground">邮箱验证码管理平台</p>
        </div>

        {/* Login Card */}
        <Card className="shadow-md">
          <CardHeader>
            <CardTitle className="text-center">管理员登录</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-6">
              {error && (
                <div className="bg-destructive/10 text-destructive p-3 rounded-lg text-sm text-center border border-destructive/20">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="username" className="text-sm font-medium text-foreground flex items-center gap-2">
                    <User className="w-4 h-4" /> 用户名
                  </label>
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="请输入用户名"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Lock className="w-4 h-4" /> 密码
                  </label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="请输入密码"
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    登录中...
                  </>
                ) : (
                  '登 录'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          © 2024 Outlooker. All rights reserved.
        </p>
      </div>
    </div>
  );
}
