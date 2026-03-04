import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Dialog } from '@/components/ui/Dialog';
import { validateBatchTags } from '@/lib/tagValidation';
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

export default function BatchTagModal({
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
  const [validationError, setValidationError] = useState<string | null>(null);
  
  if (!isOpen) return null;

  const handleSubmit = () => {
    // 清除之前的错误
    setValidationError(null);
    
    // 校验标签
    const error = validateBatchTags(batchTags);
    if (error) {
      setValidationError(error);
      return;
    }
    
    onSubmit();
  };

  const handleClose = () => {
    if (loading) return;
    setValidationError(null);
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title={`批量标签操作 (${selectedCount} 个账户)`}
      className="max-w-md"
      disableClose={loading}
    >
      <p className="sr-only">
        为选中的 {selectedCount} 个账户批量添加、移除或替换标签
      </p>

      <div className="space-y-4">
        <div>
          <Label htmlFor="batch-tag-mode" className="block text-sm font-medium mb-2">操作类型</Label>
          <select
            id="batch-tag-mode"
            value={mode}
            onChange={(e) => onModeChange(e.target.value as BatchTagMode)}
            className="w-full border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="add">添加标签</option>
            <option value="remove">移除标签</option>
            <option value="set">替换标签</option>
          </select>
        </div>

        <div>
          <Label htmlFor="batch-tag-input" className="block text-sm font-medium mb-2">
            标签 (用逗号分隔)
          </Label>
          <Input
            id="batch-tag-input"
            value={batchTags}
            onChange={(e) => {
              onTagsChange(e.target.value);
              setValidationError(null);
            }}
            placeholder="例如: VIP, 测试, 常用"
            aria-describedby="batch-tag-hint batch-tag-error"
            aria-invalid={!!validationError}
          />
          <p id="batch-tag-hint" className="text-xs text-muted-foreground mt-1">
            {mode === 'add' && '将这些标签添加到选中的账户'}
            {mode === 'remove' && '从选中的账户移除这些标签'}
            {mode === 'set' && '用这些标签替换选中账户的所有标签（留空则清除所有标签）'}
          </p>
          {validationError && (
            <div id="batch-tag-error" role="alert" className="flex items-center gap-2 text-sm text-destructive mt-2">
              <AlertCircle className="w-4 h-4" aria-hidden="true" />
              <span>{validationError}</span>
            </div>
          )}
        </div>

        <div className="flex gap-2 justify-end pt-2">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={loading}
          >
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? '处理中...' : '确认'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
