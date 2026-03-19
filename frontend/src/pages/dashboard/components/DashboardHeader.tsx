import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Inbox, LogOut, Tags, Settings2, LayoutDashboard, FileText, Shield, TimerReset, MailPlus, SplitSquareVertical } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

interface DashboardHeaderProps {
  onLogout: () => void;
}

export function DashboardHeader({ onLogout }: DashboardHeaderProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: '/admin', icon: LayoutDashboard, label: t('nav.admin') },
    { path: '/admin/outlook/accounts', icon: Shield, label: t('nav.outlookAccounts') },
    { path: '/admin/outlook/tasks', icon: TimerReset, label: t('nav.outlookTasks') },
    { path: '/admin/outlook/resources', icon: MailPlus, label: t('nav.outlookResources') },
    { path: '/admin/outlook/channels', icon: SplitSquareVertical, label: t('nav.outlookChannels') },
    { path: '/admin/tags', icon: Tags, label: t('nav.tagsManage') },
    { path: '/admin/audit', icon: FileText, label: t('nav.audit') },
    { path: '/admin/settings', icon: Settings2, label: t('nav.settings') },
  ];

  return (
    <header className="bg-background/80 backdrop-blur-md border-b px-6 py-4 flex justify-between items-center sticky top-0 z-20 shadow-sm">
      <div className="flex items-center gap-3">
        <div
          className="bg-primary p-2 rounded-xl text-primary-foreground shadow-sm cursor-pointer"
          onClick={() => navigate('/admin')}
        >
          <Inbox className="w-5 h-5" />
        </div>
        <h1
          className="text-xl font-extrabold tracking-tight cursor-pointer"
          onClick={() => navigate('/admin')}
        >
          {t('app.title')}
        </h1>
      </div>
      <div className="flex items-center gap-1">
        {navItems.map(({ path, icon: Icon, label }) => (
          <Button
            key={path}
            variant={location.pathname === path ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => navigate(path)}
            className="flex items-center gap-1.5"
          >
            <Icon className="w-4 h-4" /> {label}
          </Button>
        ))}
        <div className="w-px h-5 bg-border mx-1" />
        <LanguageSwitcher />
        <ThemeToggle />
        <Button
          variant="ghost"
          size="sm"
          onClick={onLogout}
          className="text-muted-foreground hover:text-destructive flex items-center gap-1.5"
        >
          <LogOut className="w-4 h-4" /> {t('nav.logout')}
        </Button>
      </div>
    </header>
  );
}
