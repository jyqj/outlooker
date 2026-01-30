import { Mail } from 'lucide-react';
import { VerificationSearchForm } from '@/components/VerificationSearchForm';
import { VerificationResultCard } from '@/components/VerificationResultCard';
import { LoadingCard, ErrorCard } from '@/components/StatusCard';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useVerification } from './useVerification';

export default function VerificationPage() {
  const {
    email,
    setEmail,
    loading,
    result,
    error,
    handleSearch,
    handleAutoOtp,
  } = useVerification();

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
        <VerificationSearchForm
          email={email}
          onEmailChange={setEmail}
          loading={loading}
          onSearch={handleSearch}
          onAutoOtp={handleAutoOtp}
        />

        {/* 加载状态 */}
        {loading && <LoadingCard />}

        {/* 错误提示 */}
        {error && !loading && <ErrorCard error={error} />}

        {/* 验证码结果 */}
        {result && !loading && (
          <VerificationResultCard
            result={result}
            onRefresh={() => handleSearch(undefined, true)}
          />
        )}
      </div>
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
    </div>
  );
}
