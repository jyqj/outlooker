import { useState } from 'react';

import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

type Mode = 'test-login' | 'list-proofs' | 'bind' | 'replace';

export function ProtocolBindWizard() {
  const [mode, setMode] = useState<Mode>('test-login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [verificationEmail, setVerificationEmail] = useState('');
  const [oldEmail, setOldEmail] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [staticCode, setStaticCode] = useState('');
  const [result, setResult] = useState('{}');
  const [loading, setLoading] = useState(false);

  const runAction = async () => {
    setLoading(true);
    try {
      if (mode === 'test-login') {
        const res = await api.post('/api/outlook/protocol/test-login', { email, password });
        setResult(JSON.stringify(res.data, null, 2));
      } else if (mode === 'list-proofs') {
        const res = await api.post('/api/outlook/protocol/list-proofs', { email, password });
        setResult(JSON.stringify(res.data, null, 2));
      } else if (mode === 'bind') {
        const res = await api.post('/api/outlook/protocol/bind', {
          email,
          password,
          recovery_email: recoveryEmail,
          verification_email: verificationEmail || undefined,
          static_code: staticCode,
        });
        setResult(JSON.stringify(res.data, null, 2));
      } else {
        const res = await api.post('/api/outlook/protocol/replace', {
          email,
          password,
          old_email: oldEmail,
          new_email: newEmail,
          verification_email: verificationEmail || undefined,
          static_code: staticCode,
        });
        setResult(JSON.stringify(res.data, null, 2));
      }
    } catch (error) {
      setResult(JSON.stringify({ error }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>协议绑定向导</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(['test-login', 'list-proofs', 'bind', 'replace'] as Mode[]).map((value) => (
            <Button
              key={value}
              variant={mode === value ? 'default' : 'outline'}
              onClick={() => setMode(value)}
            >
              {value}
            </Button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input placeholder="账户邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input type="password" placeholder="账户密码" value={password} onChange={(e) => setPassword(e.target.value)} />
          {(mode === 'bind' || mode === 'replace') && (
            <Input placeholder="验证码(static)" value={staticCode} onChange={(e) => setStaticCode(e.target.value)} />
          )}
          {(mode === 'bind' || mode === 'replace') && (
            <Input placeholder="验证邮箱(可选)" value={verificationEmail} onChange={(e) => setVerificationEmail(e.target.value)} />
          )}
          {mode === 'bind' && (
            <Input placeholder="新恢复邮箱" value={recoveryEmail} onChange={(e) => setRecoveryEmail(e.target.value)} />
          )}
          {mode === 'replace' && (
            <>
              <Input placeholder="旧恢复邮箱" value={oldEmail} onChange={(e) => setOldEmail(e.target.value)} />
              <Input placeholder="新恢复邮箱" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
            </>
          )}
        </div>

        <Button onClick={runAction} disabled={loading}>
          {loading ? '执行中...' : '执行协议操作'}
        </Button>

        <Textarea rows={14} value={result} onChange={(e) => setResult(e.target.value)} />
      </CardContent>
    </Card>
  );
}
