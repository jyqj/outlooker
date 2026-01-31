import { useNavigate, useLocation } from 'react-router-dom';
import { Inbox, LogOut, Tags } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface DashboardHeaderProps {
  onLogout: () => void;
}

export function DashboardHeader({ onLogout }: DashboardHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isTagsPage = location.pathname === '/admin/tags';

  return (
    <header className="bg-background/80 border-b px-6 py-4 flex justify-between items-center sticky top-0 z-20 shadow-md backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center gap-3">
        <div className="bg-primary p-2 rounded-lg text-primary-foreground">
          <Inbox className="w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold tracking-tight">Outlooker</h1>
      </div>
      <div className="flex items-center gap-4">
        <Button
          variant={isTagsPage ? "secondary" : "ghost"}
          onClick={() => navigate('/admin/tags')}
          className="flex items-center gap-2"
        >
          <Tags className="w-4 h-4" /> 标签管理
        </Button>
        <Button
          variant="ghost"
          onClick={onLogout}
          className="text-muted-foreground hover:text-destructive flex items-center gap-2"
        >
          <LogOut className="w-4 h-4" /> 退出
        </Button>
      </div>
    </header>
  );
}
