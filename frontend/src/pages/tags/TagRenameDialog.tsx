import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Dialog } from '@/components/ui/Dialog';
import type { TagRenameDialogProps } from './types';

export function TagRenameDialog({ 
  isOpen, 
  oldName,
  newName,
  loading,
  onNewNameChange,
  onConfirm, 
  onCancel 
}: TagRenameDialogProps) {
  const isValid = newName.trim() && newName !== oldName;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading && isValid) {
      e.preventDefault();
      onConfirm();
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onCancel}
      title="重命名标签"
      className="max-w-md"
    >
      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <label htmlFor="rename-tag-input" className="text-sm font-medium">
            新标签名称
          </label>
          <Input
            id="rename-tag-input"
            value={newName}
            onChange={(e) => onNewNameChange(e.target.value)}
            placeholder="输入新标签名称"
            disabled={loading}
            onKeyDown={handleKeyDown}
          />
          <p className="text-xs text-muted-foreground">
            原标签名：{oldName}
          </p>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={loading}
          >
            取消
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading || !isValid}
          >
            {loading ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
