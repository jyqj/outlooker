import React, { useState } from 'react';
import { X, Mail, Calendar, User, RefreshCw, Copy, Check } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { extractCodeFromMessage } from '../lib/utils';

export default function EmailViewModal({ email, isOpen, onClose }) {
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['email-messages', email],
    queryFn: async () => {
      const res = await api.get('/api/messages', {
        params: { email, page: 1, page_size: 1 }
      });
      return res.data;
    },
    enabled: isOpen && !!email,
  });

  if (!isOpen) return null;

  const payload = data?.data;
  const message = Array.isArray(payload) ? payload[0] : payload?.items?.[0];
  const verificationCode = message ? extractCodeFromMessage(message) : null;

  const copyCode = () => {
    if (verificationCode) {
      navigator.clipboard.writeText(verificationCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-3xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-lg">{email}</h3>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => refetch()}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="刷新"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {isLoading && (
            <div className="text-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-500">加载中...</p>
            </div>
          )}

          {isError && (
            <div className="text-center py-12">
              <p className="text-red-500">加载失败，请检查账户配置或刷新重试</p>
            </div>
          )}

          {data && !message && (
            <div className="text-center py-12">
              <Mail className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">该邮箱暂无邮件</p>
            </div>
          )}

          {message && (
            <div className="space-y-6">
              {/* Verification Code */}
              {verificationCode && (
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl border border-blue-100">
                  <h4 className="text-sm font-semibold text-blue-600 uppercase tracking-wider mb-3 text-center">
                    检测到的验证码
                  </h4>
                  <div 
                    className="flex items-center justify-center gap-4 cursor-pointer group"
                    onClick={copyCode}
                  >
                    <span className="text-4xl md:text-5xl font-mono font-bold text-gray-900 tracking-widest">
                      {verificationCode}
                    </span>
                    <button className="p-2 rounded-full bg-white shadow-sm text-gray-400 group-hover:text-blue-600 transition-colors">
                      {copied ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
              )}

              {/* Email Meta */}
              <div className="space-y-3 pb-4 border-b">
                <h2 className="text-xl font-semibold text-gray-900">
                  {message.subject || '(无主题)'}
                </h2>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-600">
                    <User className="w-4 h-4" />
                    <span className="font-medium">发件人：</span>
                    <span>{message.sender?.emailAddress?.name || message.from?.emailAddress?.name}</span>
                    <span className="text-gray-400">
                      &lt;{message.sender?.emailAddress?.address || message.from?.emailAddress?.address}&gt;
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <Calendar className="w-4 h-4" />
                    <span className="font-medium">时间：</span>
                    <span>{message.receivedDateTime ? new Date(message.receivedDateTime).toLocaleString('zh-CN') : '未知'}</span>
                  </div>
                </div>
              </div>

              {/* Email Body */}
              <div className="prose max-w-none">
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 max-h-96 overflow-y-auto">
                  {message.body?.contentType === 'html' ? (
                    <div dangerouslySetInnerHTML={{ __html: message.body.content }} />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm">{message.body?.content}</pre>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
