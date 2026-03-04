import { useTranslation } from 'react-i18next';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { TagDeleteDialogProps } from './types';

export function TagDeleteDialog({ 
  isOpen, 
  tagName, 
  loading,
  onConfirm, 
  onCancel 
}: TagDeleteDialogProps) {
  const { t } = useTranslation();
  return (
    <ConfirmDialog
      isOpen={isOpen}
      onClose={onCancel}
      onConfirm={onConfirm}
      title={t('tags.deleteConfirmTitle')}
      message={t('tags.deleteConfirm', { name: tagName })}
      confirmText={t('tags.delete')}
      cancelText={t('common.cancel')}
      variant="danger"
      loading={loading}
    />
  );
}
