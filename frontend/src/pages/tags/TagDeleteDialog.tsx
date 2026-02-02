import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { TagDeleteDialogProps } from './types';

export function TagDeleteDialog({ 
  isOpen, 
  tagName, 
  loading,
  onConfirm, 
  onCancel 
}: TagDeleteDialogProps) {
  return (
    <ConfirmDialog
      isOpen={isOpen}
      onClose={onCancel}
      onConfirm={onConfirm}
      title="确认删除标签"
      message={`确定要删除标签 "${tagName}" 吗？该标签将从所有账户中移除，此操作不可恢复。`}
      confirmText="删除"
      cancelText="取消"
      variant="danger"
      loading={loading}
    />
  );
}
