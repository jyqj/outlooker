import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Button } from './ui/Button';

/**
 * 验证码高亮展示卡片组件
 * - 大字号显示验证码
 * - 支持点击整体或按钮复制
 * - 展示复制成功提示
 */
export default function VerificationCodeCard({ code, showFallback = false }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasCode = Boolean(code);

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 p-6 rounded-xl border-2 border-primary shadow-lg">
      <h4 className="text-sm font-bold text-primary dark:text-blue-300 uppercase tracking-wide mb-4 text-center">
        {hasCode ? '🔐 检测到的验证码' : '🔍 暂未检测到验证码'}
      </h4>
      {hasCode ? (
        <div
          className="flex items-center justify-center gap-3 cursor-pointer group bg-white dark:bg-gray-800 p-5 rounded-lg hover:shadow-md transition-all border-2 border-primary dark:border-blue-400"
          onClick={handleCopy}
          title="点击复制验证码"
        >
          <span className="text-5xl md:text-6xl font-mono font-black tracking-wider text-primary dark:text-blue-300 select-all">
            {code}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full hover:bg-primary/20 shrink-0"
          >
            {copied ? (
              <Check className="w-6 h-6 text-green-600" />
            ) : (
              <Copy className="w-6 h-6 text-primary dark:text-blue-300" />
            )}
          </Button>
        </div>
      ) : (
        showFallback && (
          <div className="text-center py-4">
            <p className="text-muted-foreground">未自动识别到验证码</p>
            <p className="text-sm text-muted-foreground mt-1">请查看下方邮件正文</p>
          </div>
        )
      )}
      {copied && (
        <p className="text-center text-sm text-green-600 dark:text-green-400 mt-3 font-semibold animate-in fade-in duration-200">
          ✓ 已复制到剪贴板
        </p>
      )}
    </div>
  );
}


