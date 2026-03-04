import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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
      title={t('tags.renameTitle')}
      className="max-w-md"
    >
      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <label htmlFor="rename-tag-input" className="text-sm font-medium">
            {t('tags.newName')}
          </label>
          <Input
            id="rename-tag-input"
            value={newName}
            onChange={(e) => onNewNameChange(e.target.value)}
            placeholder={t('tags.renamePlaceholder')}
            disabled={loading}
            onKeyDown={handleKeyDown}
          />
          <p className="text-xs text-muted-foreground">
            {t('tags.renameOriginal', { name: oldName })}
          </p>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={loading}
          >
            {t('common.cancel')}
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading || !isValid}
          >
            {loading ? t('tags.saving') : t('common.save')}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
