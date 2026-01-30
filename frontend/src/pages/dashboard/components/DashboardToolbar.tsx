import { Search, Upload, Download, RefreshCw, Trash2, Tags } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';

interface DashboardToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  selectedCount: number;
  batchLoading: boolean;
  exporting: boolean;
  onBatchDelete: () => void;
  onOpenBatchTagModal: () => void;
  onClearSelection: () => void;
  onImport: () => void;
  onExport: () => void;
  onRefresh: () => void;
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
}: DashboardToolbarProps) {
  return (
    <Card className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
      <div className="relative w-full md:w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
        <Input
          type="text"
          placeholder="搜索邮箱..."
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
              删除 ({selectedCount})
            </Button>
            <Button
              variant="outline"
              onClick={onOpenBatchTagModal}
              disabled={batchLoading}
              className="gap-2"
            >
              <Tags className="w-4 h-4" />
              批量标签
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="text-muted-foreground"
            >
              取消选择
            </Button>
          </>
        )}
        <Button onClick={onImport} className="flex-1 md:flex-none gap-2">
          <Upload className="w-4 h-4" /> 导入
        </Button>
        <Button
          variant="outline"
          onClick={onExport}
          disabled={exporting}
          className="flex-1 md:flex-none gap-2"
        >
          <Download className={`w-4 h-4 ${exporting ? 'animate-pulse' : ''}`} />
          {exporting ? '导出中...' : '导出'}
        </Button>
        <Button variant="outline" size="icon" onClick={onRefresh} title="刷新">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
