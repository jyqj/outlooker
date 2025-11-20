import React, { useState } from 'react';
import { Search, Mail, Key, RefreshCw, Copy, Check } from 'lucide-react';
import api from '../lib/api';
import { cn, extractCodeFromMessage, logError } from '../lib/utils';

export default function VerificationPage() {
  const [email, setEmail] = useState('');
  const [refreshToken, setRefreshToken] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!email) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setCopied(false);

    try {
      let response;
      if (refreshToken) {
        // 临时账户模式
        response = await api.post('/api/temp-messages', {
          email,
          refresh_token: refreshToken,
          page_size: 1,
          page: 1,
          search: ''
        });
      } else {
        // 数据库账户模式
        response = await api.get('/api/messages', {
          params: { email, page_size: 1, page: 1 }
        });
      }

      if (response.data.success) {
        const payload = response.data.data;
        const messages = Array.isArray(payload) ? payload : payload?.items;
        if (messages && messages.length > 0) {
          const msg = messages[0];
          // 提取验证码（使用抽象后的方法）
          const code = extractCodeFromMessage(msg);

          setResult({
            ...msg,
            extractedCode: code
          });
        } else {
          setError('未找到邮件');
        }
      } else {
        const msg = response.data?.message;
        // 如果是邮箱未配置的错误，且用户没有提供 refresh_token，则提示并展开高级选项
        if (!refreshToken && (typeof msg === 'string' && (msg.includes('未在配置中找到') || msg.includes('未配置')))) {
          setError('该邮箱未配置。请提供 Refresh Token 使用临时模式，或联系管理员。');
          setShowAdvanced(true);
        } else {
          setError(msg || '获取失败');
        }
      }
    } catch (err) {
      logError('获取验证码失败', err);
      setError(err.response?.data?.message || '网络请求失败');
    } finally {
      setLoading(false);
    }
  };

  const copyCode = () => {
    if (result?.extractedCode) {
      navigator.clipboard.writeText(result.extractedCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8">
        {/* 标题区 */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Outlook 验证码提取
          </h1>
          <p className="text-gray-500">
            输入邮箱地址，快速获取最新验证码
          </p>
        </div>

        {/* 搜索卡片 */}
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 space-y-6 transition-all duration-300 hover:shadow-2xl">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Mail className="w-4 h-4" /> 邮箱地址
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@outlook.com"
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-lg"
                required
              />
            </div>

            {showAdvanced && (
              <div className="space-y-2 animate-in fade-in slide-in-from-top-4 duration-300">
                <label htmlFor="token" className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <Key className="w-4 h-4" /> Refresh Token (可选 - 用于临时查询)
                </label>
                <textarea
                  id="token"
                  value={refreshToken}
                  onChange={(e) => setRefreshToken(e.target.value)}
                  placeholder="如果邮箱未在系统配置，请输入 refresh_token..."
                  className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm font-mono h-24 resize-none"
                />
              </div>
            )}

            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  "flex-1 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium text-lg flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-600/20",
                  loading && "opacity-70 cursor-not-allowed"
                )}
              >
                {loading ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <Search className="w-5 h-5" />
                )}
                {loading ? '获取中...' : '获取最新验证码'}
              </button>
              
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="px-4 py-3 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors text-sm font-medium"
              >
                {showAdvanced ? '收起选项' : '高级选项'}
              </button>
            </div>
          </form>
        </div>

        {/* 结果展示区 */}
        {error && (
          <div className="bg-red-50 border border-red-100 text-red-600 px-6 py-4 rounded-xl animate-in fade-in slide-in-from-bottom-4">
            <p className="flex items-center gap-2 font-medium">
              ⚠️ {error}
            </p>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-500">
            {/* 验证码高亮区 */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-8 text-center border-b border-blue-100">
              <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider mb-2">
                检测到的验证码
              </h3>
              {result.extractedCode ? (
                <div 
                  className="flex items-center justify-center gap-4 cursor-pointer group"
                  onClick={copyCode}
                >
                  <span className="text-5xl md:text-6xl font-mono font-bold text-gray-900 tracking-widest">
                    {result.extractedCode}
                  </span>
                  <button className="p-2 rounded-full bg-white shadow-sm text-gray-400 group-hover:text-blue-600 transition-colors">
                    {copied ? <Check className="w-6 h-6 text-green-500" /> : <Copy className="w-6 h-6" />}
                  </button>
                </div>
              ) : (
                <p className="text-gray-500 italic text-lg">未自动识别到验证码，请查看下方正文</p>
              )}
            </div>

            {/* 邮件详情 */}
            <div className="p-6 md:p-8 space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-100">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 leading-snug">
                    {result.subject || '(无主题)'}
                  </h2>
                  <div className="mt-1 text-gray-500 flex items-center gap-2 text-sm">
                    <span className="font-medium text-gray-700">
                      {result.sender?.emailAddress?.name || result.from?.emailAddress?.name}
                    </span>
                    <span>&lt;{result.sender?.emailAddress?.address || result.from?.emailAddress?.address}&gt;</span>
                  </div>
                </div>
                <div className="text-sm text-gray-400 font-mono bg-gray-50 px-3 py-1 rounded-full whitespace-nowrap">
                  {result.receivedDateTime ? new Date(result.receivedDateTime).toLocaleString() : '未知时间'}
                </div>
              </div>

              <div className="prose max-w-none text-gray-800 bg-gray-50 p-4 rounded-lg border border-gray-100 max-h-96 overflow-y-auto">
                {result.body.contentType === 'html' ? (
                    <div dangerouslySetInnerHTML={{ __html: result.body.content }} />
                ) : (
                    <pre className="whitespace-pre-wrap font-sans">{result.body.content}</pre>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
