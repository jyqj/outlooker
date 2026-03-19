import { Mail, Shield, Smartphone } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface AuthMethodsPanelProps {
  data: Record<string, unknown>;
}

function getItems(data: Record<string, unknown>, key: string): Array<Record<string, unknown>> {
  const value = data[key];
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

export function AuthMethodsPanel({ data }: AuthMethodsPanelProps) {
  const emailMethods = getItems(data, 'email_methods');
  const totpMethods = getItems(data, 'totp_methods');
  const phoneMethods = getItems(data, 'phone_methods');

  const sections = [
    { key: 'email', title: '恢复邮箱', icon: Mail, items: emailMethods, valueKey: 'emailAddress' },
    { key: 'totp', title: 'TOTP', icon: Shield, items: totpMethods, valueKey: 'displayName' },
    { key: 'phone', title: '手机号', icon: Smartphone, items: phoneMethods, valueKey: 'phoneNumber' },
  ];

  return (
    <div className="grid grid-cols-1 gap-4">
      {sections.map(({ key, title, icon: Icon, items, valueKey }) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icon className="w-5 h-5" />
              {title}
              <Badge variant="outline">{items.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无 {title}。</p>
            ) : (
              items.map((item, index) => (
                <div key={String(item.id ?? index)} className="rounded-lg border p-3 space-y-1">
                  <div className="font-medium">{String(item[valueKey] ?? item.id ?? 'N/A')}</div>
                  <div className="text-xs text-muted-foreground">ID: {String(item.id ?? 'N/A')}</div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
