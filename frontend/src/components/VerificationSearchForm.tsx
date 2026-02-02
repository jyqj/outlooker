import type { FormEvent } from 'react';
import { Mail, Loader2, Wand2, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent } from '@/components/ui/Card';

interface VerificationSearchFormProps {
  email: string;
  onEmailChange: (value: string) => void;
  loading: boolean;
  onSearch: (e?: FormEvent) => void;
  onAutoOtp?: () => void;
  showAutoOtp?: boolean;
}

export function VerificationSearchForm({
  email,
  onEmailChange,
  loading,
  onSearch,
  onAutoOtp,
  showAutoOtp = false,
}: VerificationSearchFormProps) {
  return (
    <Card className="shadow-md">
      <CardContent className="pt-6">
        <form onSubmit={onSearch} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="email"
              className="text-sm font-medium text-foreground flex items-center gap-2"
            >
              <Mail className="w-4 h-4" /> 邮箱地址
            </label>
            <div className="relative">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => onEmailChange(e.target.value)}
                placeholder="example@outlook.com"
                className={`text-base ${email ? 'pr-10' : ''}`}
                required
                disabled={loading}
              />
              {email && !loading && (
                <button
                  type="button"
                  onClick={() => onEmailChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-full p-0.5 transition-colors"
                  aria-label="清除输入内容"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
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
            {showAutoOtp && onAutoOtp && (
              <Button
                type="button"
                variant="outline"
                disabled={loading}
                onClick={onAutoOtp}
                className="w-full md:w-auto gap-2 text-base font-semibold py-4"
                size="lg"
              >
                <Wand2 className="w-5 h-5" />
                自动分配邮箱并接码
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
