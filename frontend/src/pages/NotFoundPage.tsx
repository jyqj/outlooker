import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-muted/60 px-4">
      <div className="text-center space-y-6 max-w-md">
        {/* 404 Number */}
        <div className="relative">
          <h1 className="text-[150px] font-bold text-muted-foreground/20 leading-none select-none">
            404
          </h1>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-primary/10 p-4 rounded-full">
              <Home className="w-12 h-12 text-primary" />
            </div>
          </div>
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-foreground">
            页面未找到
          </h2>
          <p className="text-muted-foreground">
            抱歉，您访问的页面不存在或已被移除。
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild variant="default" className="gap-2">
            <Link to="/">
              <Home className="w-4 h-4" />
              返回首页
            </Link>
          </Button>
          <Button asChild variant="outline" className="gap-2">
            <Link to="/admin">
              <ArrowLeft className="w-4 h-4" />
              管理后台
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
