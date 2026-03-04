import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import {
  Settings2,
  Globe,
  RefreshCw,
  Bell,
  Mail,
  Save,
  Loader2,
  Trash2,
  Info,
  ArrowLeft,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { useSystemConfigQuery, useApiAction } from '@/lib/hooks';
import { queryKeys } from '@/lib/queryKeys';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { SystemConfig } from '@/types';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? 'bg-primary' : 'bg-muted-foreground/25'
      }`}
    >
      <span
        className={`pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

const DEFAULT_CONFIG: SystemConfig = {
  email_limit: 5,
  proxy_enabled: false,
  proxy_url: '',
  token_refresh_enabled: true,
  token_refresh_interval_hours: 12,
  webhook_enabled: false,
  webhook_url: '',
  webhook_secret: '',
  webhook_events: 'verification_code_received,token_refresh_failed',
};

export default function SettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: configData, isLoading: configLoading } = useSystemConfigQuery();
  const apiAction = useApiAction();

  const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG);
  const [saving, setSaving] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (configData?.data) {
      setConfig({ ...DEFAULT_CONFIG, ...configData.data });
      setDirty(false);
    }
  }, [configData]);

  const updateField = <K extends keyof SystemConfig>(key: K, value: SystemConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(config)) {
        if (k in DEFAULT_CONFIG) payload[k] = v;
      }
      await apiAction(
        () => api.put('/api/system/config', { configs: payload }),
        {
          successMessage: t('settingsPage.saveSuccess'),
          errorMessage: t('settingsPage.saveFailed'),
          onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.systemConfig() });
            setDirty(false);
          },
        },
      );
    } finally {
      setSaving(false);
    }
  };

  const handleClearCache = async () => {
    setClearingCache(true);
    try {
      await apiAction(
        () => api.post('/api/system/cache/refresh'),
        {
          successMessage: t('settingsPage.cacheCleared'),
          errorMessage: t('settingsPage.cacheClearFailed'),
          onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.systemMetrics() });
            queryClient.invalidateQueries({ queryKey: queryKeys.accounts() });
          },
        },
      );
    } finally {
      setClearingCache(false);
    }
  };

  const handleLogout = async () => {
    const { clearAuthTokens } = await import('@/lib/api');
    try {
      await api.post('/api/admin/logout', {});
    } catch { /* ignore */ }
    clearAuthTokens();
    navigate('/admin/login');
  };

  if (configLoading) {
    return (
      <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
        <DashboardHeader onLogout={handleLogout} />
        <main className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      <DashboardHeader onLogout={handleLogout} />

      <main className="flex-1 p-6 max-w-4xl mx-auto w-full space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin')} className="gap-1.5">
              <ArrowLeft className="w-4 h-4" />
              {t('common.back')}
            </Button>
            <div>
              <h2 className="text-2xl font-bold tracking-tight">{t('settingsPage.title')}</h2>
              <p className="text-sm text-muted-foreground">{t('settingsPage.subtitle')}</p>
            </div>
          </div>
          <Button onClick={handleSave} disabled={saving || !dirty} className="gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? t('settingsPage.saving') : t('settingsPage.save')}
          </Button>
        </div>

        {/* Email Fetching */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="w-4 h-4 text-primary" />
              {t('settingsPage.email.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{t('settingsPage.email.limit')}</div>
                <div className="text-xs text-muted-foreground">{t('settingsPage.email.limitDesc')}</div>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={config.email_limit}
                  onChange={(e) => updateField('email_limit', Number(e.target.value) || 5)}
                  className="w-20 text-center"
                />
                <span className="text-sm text-muted-foreground">{t('settingsPage.email.perFetch')}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Proxy Settings */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Globe className="w-4 h-4 text-primary" />
              {t('settingsPage.proxy.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{t('settingsPage.proxy.enable')}</div>
                <div className="text-xs text-muted-foreground">{t('settingsPage.proxy.enableDesc')}</div>
              </div>
              <Toggle checked={config.proxy_enabled} onChange={(v) => updateField('proxy_enabled', v)} />
            </div>
            {config.proxy_enabled && (
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('settingsPage.proxy.url')}</label>
                <Input
                  placeholder="http://127.0.0.1:7890 or socks5://127.0.0.1:1080"
                  value={config.proxy_url}
                  onChange={(e) => updateField('proxy_url', e.target.value)}
                />
                <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  <span>{t('settingsPage.proxy.hint')}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Token Auto-Refresh */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <RefreshCw className="w-4 h-4 text-primary" />
              {t('settingsPage.tokenRefresh.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{t('settingsPage.tokenRefresh.enable')}</div>
                <div className="text-xs text-muted-foreground">{t('settingsPage.tokenRefresh.enableDesc')}</div>
              </div>
              <Toggle
                checked={config.token_refresh_enabled}
                onChange={(v) => updateField('token_refresh_enabled', v)}
              />
            </div>
            {config.token_refresh_enabled && (
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{t('settingsPage.tokenRefresh.interval')}</div>
                  <div className="text-xs text-muted-foreground">{t('settingsPage.tokenRefresh.intervalDesc')}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={1}
                    max={168}
                    value={config.token_refresh_interval_hours}
                    onChange={(e) => updateField('token_refresh_interval_hours', Number(e.target.value) || 12)}
                    className="w-20 text-center"
                  />
                  <span className="text-sm text-muted-foreground">{t('settingsPage.tokenRefresh.hours')}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Webhook */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Bell className="w-4 h-4 text-primary" />
              {t('settingsPage.webhook.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{t('settingsPage.webhook.enable')}</div>
                <div className="text-xs text-muted-foreground">{t('settingsPage.webhook.enableDesc')}</div>
              </div>
              <Toggle
                checked={config.webhook_enabled}
                onChange={(v) => updateField('webhook_enabled', v)}
              />
            </div>
            {config.webhook_enabled && (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('settingsPage.webhook.url')}</label>
                  <Input
                    placeholder="https://example.com/webhook"
                    value={config.webhook_url}
                    onChange={(e) => updateField('webhook_url', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('settingsPage.webhook.secret')}</label>
                  <Input
                    type="password"
                    placeholder={t('settingsPage.webhook.secretPlaceholder')}
                    value={config.webhook_secret}
                    onChange={(e) => updateField('webhook_secret', e.target.value)}
                  />
                  <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>{t('settingsPage.webhook.secretHint')}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('settingsPage.webhook.events')}</label>
                  <Input
                    placeholder="verification_code_received,token_refresh_failed"
                    value={config.webhook_events}
                    onChange={(e) => updateField('webhook_events', e.target.value)}
                  />
                  <div className="text-xs text-muted-foreground">{t('settingsPage.webhook.eventsHint')}</div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Maintenance */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Settings2 className="w-4 h-4 text-primary" />
              {t('settingsPage.maintenance.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{t('settingsPage.maintenance.clearCache')}</div>
                <div className="text-xs text-muted-foreground">{t('settingsPage.maintenance.clearCacheDesc')}</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearCache}
                disabled={clearingCache}
                className="gap-1.5"
              >
                {clearingCache
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <Trash2 className="w-3.5 h-3.5" />
                }
                {clearingCache ? t('settingsPage.maintenance.clearing') : t('settingsPage.maintenance.clear')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
