import { useTranslation } from 'react-i18next';
import { Search, Upload, Download, RefreshCw, Trash2, Tags, Loader2, HeartPulse } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';

interface DashboardToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  selectedCount: number;
  batchLoading: boolean;
  exporting: boolean;
  healthChecking?: boolean;
  onBatchDelete: () => void;
  onOpenBatchTagModal: () => void;
  onClearSelection: () => void;
  onImport: () => void;
  onExport: () => void;
  onRefresh: () => void;
  onHealthCheck?: () => void;
}

export function DashboardToolbar({
  search,
  onSearchChange,
  selectedCount,
  batchLoading,
  exporting,
  onBatchDelete,
  onOpenBatchTagModal,
  onClearSelection,
  onImport,
  onExport,
  onRefresh,
  healthChecking,
  onHealthCheck,
}: DashboardToolbarProps) {
  const { t } = useTranslation();
  return (
    <Card className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
      <div className="relative w-full md:w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
        <Input
          type="text"
          placeholder={t('dashboard.searchPlaceholder')}
          className="pl-10"
          value={search}
          onChange={e => onSearchChange(e.target.value)}
        />
      </div>

      <div className="flex gap-2 w-full md:w-auto flex-wrap">
        {selectedCount > 0 && (
          <>
            <Button
              variant="destructive"
              onClick={onBatchDelete}
              disabled={batchLoading}
              className="gap-2"
            >
              <Trash2 className="w-4 h-4" />
              {t('dashboard.toolbar.delete', { count: selectedCount })}
            </Button>
            <Button
              variant="outline"
              onClick={onOpenBatchTagModal}
              disabled={batchLoading}
              className="gap-2"
            >
              <Tags className="w-4 h-4" />
              {t('dashboard.toolbar.batchTag')}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="text-muted-foreground"
            >
              {t('dashboard.toolbar.cancelSelection')}
            </Button>
          </>
        )}
        <Button onClick={onImport} className="flex-1 md:flex-none gap-2">
          <Upload className="w-4 h-4" /> {t('dashboard.toolbar.import')}
        </Button>
        <Button
          variant="outline"
          onClick={onExport}
          disabled={exporting}
          className="flex-1 md:flex-none gap-2"
        >
          {exporting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          {exporting ? t('dashboard.toolbar.exporting') : t('dashboard.toolbar.export')}
        </Button>
        {onHealthCheck && (
          <Button
            variant="outline"
            onClick={onHealthCheck}
            disabled={healthChecking}
            className="gap-1.5"
            title={t('dashboard.toolbar.healthCheck')}
          >
            {healthChecking
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <HeartPulse className="w-4 h-4" />
            }
            {healthChecking ? t('dashboard.toolbar.checking') : t('dashboard.toolbar.healthCheck')}
          </Button>
        )}
        <Button variant="outline" size="icon" onClick={onRefresh} title={t('dashboard.toolbar.refresh')}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
