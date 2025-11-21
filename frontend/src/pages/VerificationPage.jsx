import React, { useState } from 'react';
import { Mail, RefreshCw, Loader2, AlertCircle, Wand2 } from 'lucide-react';
import api from '../lib/api';
import { extractCodeFromMessage, logError } from '../lib/utils';
import { sanitizeHtml } from '../lib/sanitize';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import VerificationCodeCard from '../components/VerificationCodeCard';

export default function VerificationPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!email) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // 只使用数据库账户模式
      const response = await api.get('/api/messages', {
        params: { email, page_size: 1, page: 1 }
      });

      if (response.data.success) {
        const payload = response.data.data;
        const messages = Array.isArray(payload) ? payload : payload?.items;
        if (messages && messages.length > 0) {
          const msg = messages[0];
          // 提取验证码
          const code = extractCodeFromMessage(msg);

          setResult({
            ...msg,
            extractedCode: code
          });
        } else {
          setError('该邮箱暂无邮件');
        }
      } else {
        setError(response.data?.message || '获取失败');
      }
    } catch (err) {
      logError('获取验证码失败', err);
      setError(err.response?.data?.message || '网络请求失败，请检查邮箱地址是否正确');
    } finally {
      setLoading(false);
    }
  };

  const handleAutoOtp = async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // 1. 获取一个未使用的邮箱
      const unusedRes = await api.get('/api/public/account-unused');
      const unusedPayload = unusedRes.data;

      if (!unusedPayload?.success || !unusedPayload?.data?.email) {
        setError(unusedPayload?.message || '暂无可用邮箱，请稍后重试');
        return;
      }

      const autoEmail = unusedPayload.data.email;
      setEmail(autoEmail);

      // 2. 调用 OTP 接口获取验证码
      const otpRes = await api.get(
        `/api/public/account/${encodeURIComponent(autoEmail)}/otp`,
      );
      const otpPayload = otpRes.data;

      if (!otpPayload?.success || !otpPayload?.data?.code) {
        setError(otpPayload?.message || '未自动识别到验证码');
        return;
      }

      const code = otpPayload.data.code;

      // 3. 构造一个简化的 result 供 UI 展示
      setResult({
        subject: '(自动接码)',
        body: { content: '', contentType: 'text' },
        bodyPreview: '',
        sender: { emailAddress: { name: 'Outlooker', address: '' } },
        receivedDateTime: new Date().toISOString(),
        extractedCode: code,
      });

      // 4. 标记该邮箱为已使用（失败不影响主流程）
      try {
        await api.post(
          `/api/public/account/${encodeURIComponent(autoEmail)}/used`,
        );
      } catch (markErr) {
        logError('标记邮箱为已使用失败', markErr);
      }
    } catch (err) {
      logError('自动获取验证码失败', err);
      setError(
        err.response?.data?.message || '自动获取验证码失败，请稍后重试',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-3xl space-y-6">
        {/* 标题区 */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="bg-primary/10 p-3 rounded-lg">
              <Mail className="w-8 h-8 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            获取邮箱验证码
          </h1>
          <p className="text-muted-foreground">
            输入邮箱地址，快速获取最新验证码
          </p>
        </div>

        {/* 搜索卡片 */}
        <Card className="shadow-md">
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium text-foreground flex items-center gap-2">
                  <Mail className="w-4 h-4" /> 邮箱地址
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="example@outlook.com"
                  className="text-base"
                  required
                  disabled={loading}
                />
              </div>

              <div className="flex flex-col md:flex-row gap-3">
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full gap-2 text-lg font-semibold py-6 border-2 transition-all"
                  size="lg"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      获取中...
                    </>
                  ) : (
                    <>
                      <Mail className="w-6 h-6" />
                      获取最新验证码
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={handleAutoOtp}
                  className="w-full md:w-auto gap-2 text-base font-semibold py-4"
                  size="lg"
                >
                  <Wand2 className="w-5 h-5" />
                  自动分配邮箱并接码
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* 加载状态 */}
        {loading && (
          <Card className="shadow-md">
            <CardContent className="py-12">
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="relative">
                  <Loader2 className="w-12 h-12 text-primary animate-spin" />
                  <div className="absolute inset-0 w-12 h-12 border-4 border-primary/20 rounded-full"></div>
                </div>
                <div className="text-center space-y-1">
                  <p className="font-semibold text-foreground">正在获取邮件...</p>
                  <p className="text-sm text-muted-foreground">请稍候</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 错误提示 */}
        {error && !loading && (
          <Card className="shadow-md border-destructive/50">
            <CardContent className="py-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-destructive">{error}</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    请检查邮箱地址是否正确，或联系管理员确认该邮箱已配置
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 验证码结果 */}
        {result && !loading && (
          <Card className="shadow-md">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">验证码</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSearch()}
                  className="gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  刷新
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 验证码高亮区 */}
              <VerificationCodeCard
                code={result.extractedCode}
                showFallback
              />

              {/* 邮件元信息 */}
              <div className="space-y-3 text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
                <div>
                  <h3 className="font-semibold text-foreground mb-2">邮件主题</h3>
                  <p className="text-foreground">{result.subject || '(无主题)'}</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-gray-200 dark:border-gray-800">
                  <div>
                    <span className="font-semibold text-foreground block mb-1">发件人</span>
                    <div className="text-foreground">
                      <span className="font-medium">
                        {result.sender?.emailAddress?.name || result.from?.emailAddress?.name || '未知'}
                      </span>
                      <br />
                      <span className="text-xs text-gray-600 dark:text-gray-400 break-all">
                        {result.sender?.emailAddress?.address || result.from?.emailAddress?.address || '未知'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="font-semibold text-foreground block mb-1">接收时间</span>
                    <span className="text-foreground">
                      {result.receivedDateTime ? new Date(result.receivedDateTime).toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      }) : '未知'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 邮件正文 */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                  📧 邮件正文
                </h3>
                <div className="bg-gray-50 dark:bg-gray-900 p-5 rounded-lg border border-gray-200 dark:border-gray-800 max-h-96 overflow-y-auto">
                  {result.body?.contentType === 'html' ? (
                    <div
                      className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-p:text-foreground prose-a:text-primary [&_*]:text-foreground"
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(result.body.content) }}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">
                      {result.body?.content || '(无内容)'}
                    </pre>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
