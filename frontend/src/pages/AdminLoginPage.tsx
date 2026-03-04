import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Lock, User, Inbox, Loader2, Eye, EyeOff } from 'lucide-react';
import api, { setAuthTokens } from '@/lib/api';
import { handleApiError } from '@/lib/error';
import { useAsyncTask } from '@/lib/hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { AdminLoginResponse } from '@/types/models';

export default function AdminLoginPage() {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
          setError(t('login.error.responseError'));
        }
      });
    } catch (err) {
      setError(handleApiError(err, 'Login failed', t('login.error.loginFailed')));
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
            <h1 className="text-3xl font-bold tracking-tight">{t('app.title')}</h1>
          </div>
          <p className="text-muted-foreground">{t('login.subtitle')}</p>
        </div>

        {/* Login Card */}
        <Card className="shadow-md">
          <CardHeader>
            <CardTitle className="text-center">{t('login.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-6" aria-describedby={error ? "login-error" : undefined}>
              {error && (
                <div id="login-error" role="alert" className="bg-destructive/10 text-destructive p-3 rounded-lg text-sm text-center border border-destructive/20">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="username" className="text-sm font-medium text-foreground flex items-center gap-2">
                    <User className="w-4 h-4" /> {t('login.username')}
                  </label>
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={t('login.usernamePlaceholder')}
                    required
                    disabled={loading}
                    autoFocus
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Lock className="w-4 h-4" /> {t('login.password')}
                  </label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t('login.passwordPlaceholder')}
                      required
                      disabled={loading}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition-all duration-150 hover:bg-muted-foreground/10 hover:text-foreground active:scale-[var(--scale-click-icon)] focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                      aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
                      disabled={loading}
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
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
                    {t('login.loggingIn')}
                  </>
                ) : (
                  t('login.loginButton')
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          {t('app.copyright', { year: new Date().getFullYear() })}
        </p>
      </div>
    </div>
  );
}
