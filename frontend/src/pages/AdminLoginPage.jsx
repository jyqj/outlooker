import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User, Inbox, Loader2 } from 'lucide-react';
import api from '../lib/api';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export default function AdminLoginPage() {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await api.post('/api/admin/login', {
        username,
        password
      });

      if (response.data.access_token) {
        sessionStorage.setItem('admin_token', response.data.access_token);
        navigate('/admin');
      } else {
        setError('登录响应格式错误');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('登录失败，请检查用户名或密码');
    } finally {
      setLoading(false);
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

