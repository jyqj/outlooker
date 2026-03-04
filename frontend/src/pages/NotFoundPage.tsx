import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function NotFoundPage() {
  const { t } = useTranslation();
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
            {t('notFound.title')}
          </h2>
          <p className="text-muted-foreground">
            {t('notFound.message')}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild variant="default" className="gap-2">
            <Link to="/">
              <Home className="w-4 h-4" />
              {t('notFound.home')}
            </Link>
          </Button>
          <Button asChild variant="outline" className="gap-2">
            <Link to="/admin">
              <ArrowLeft className="w-4 h-4" />
              {t('notFound.admin')}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
