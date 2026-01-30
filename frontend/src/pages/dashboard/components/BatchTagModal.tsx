import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import type { BatchTagMode } from '../hooks/useBatchOperations';

interface BatchTagModalProps {
  isOpen: boolean;
  mode: BatchTagMode;
  selectedCount: number;
  batchTags: string;
  loading: boolean;
  onTagsChange: (tags: string) => void;
  onModeChange: (mode: BatchTagMode) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function BatchTagModal({
  isOpen,
  mode,
  selectedCount,
  batchTags,
  loading,
  onTagsChange,
  onModeChange,
  onSubmit,
  onClose,
}: BatchTagModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-lg font-semibold mb-4">
          批量标签操作 ({selectedCount} 个账户)
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">操作类型</label>
            <select
              value={mode}
              onChange={(e) => onModeChange(e.target.value as BatchTagMode)}
              className="w-full border rounded-md px-3 py-2 bg-background"
            >
              <option value="add">添加标签</option>
              <option value="remove">移除标签</option>
              <option value="set">替换标签</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">
              标签 (用逗号分隔)
            </label>
            <Input
              value={batchTags}
              onChange={(e) => onTagsChange(e.target.value)}
              placeholder="例如: VIP, 测试, 常用"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {mode === 'add' && '将这些标签添加到选中的账户'}
              {mode === 'remove' && '从选中的账户移除这些标签'}
              {mode === 'set' && '用这些标签替换选中账户的所有标签（留空则清除所有标签）'}
            </p>
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              取消
            </Button>
            <Button
              onClick={onSubmit}
              disabled={loading}
            >
              {loading ? '处理中...' : '确认'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
