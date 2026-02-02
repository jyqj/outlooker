import React, { useState } from 'react';
import { X, Plus, AlertCircle } from 'lucide-react';
import { Dialog } from './ui/Dialog';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Badge } from './ui/Badge';
import api from '@/lib/api';
import { useApiAction } from '@/lib/hooks';
import { MESSAGES } from '@/lib/constants';
import { TAG_RULES, validateTag } from '@/lib/tagValidation';

interface TagManageModalContentProps {
  email: string;
  currentTags: string[];
  onClose: () => void;
  onSuccess?: () => void;
}

// 内部组件,用于在 modal 打开时重置状态
function TagManageModalContent({ email, currentTags = [], onClose, onSuccess }: TagManageModalContentProps) {
  const [tags, setTags] = useState<string[]>(currentTags || []);
  const [newTag, setNewTag] = useState('');
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const apiAction = useApiAction();

  const handleAddTag = (e?: React.FormEvent) => {
    e?.preventDefault();
    const tag = newTag.trim();
    
    // 清除之前的错误
    setValidationError(null);
    
    // 校验标签
    const error = validateTag(tag, tags);
    if (error) {
      setValidationError(error);
      return;
    }
    
    setTags([...tags, tag]);
    setNewTag('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  const handleSave = async () => {
    setSaving(true);
    await apiAction(
      () =>
        api.post(`/api/accounts/${encodeURIComponent(email)}/tags`, {
          email,
          tags,
        }),
      {
        successMessage: MESSAGES.SUCCESS_TAG_SAVED,
        errorMessage: MESSAGES.ERROR_TAG_SAVE_FAILED,
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      },
    );
    setSaving(false);
  };

  return (
    <div className="space-y-6 py-4">
      <div className="bg-muted/60 p-3 rounded-lg border border-border/50">
        <p className="text-sm text-muted-foreground mb-1">正在编辑账户：</p>
        <p className="font-medium text-foreground break-all">{email}</p>
      </div>

      <div className="space-y-3">
        <label htmlFor="new-tag-input" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
          添加新标签 ({tags.length}/{TAG_RULES.MAX_COUNT})
        </label>
        <form onSubmit={handleAddTag} className="flex gap-2">
          <Input
            id="new-tag-input"
            value={newTag}
            onChange={(e) => {
              setNewTag(e.target.value);
              setValidationError(null);
            }}
            placeholder="输入标签名称..."
            className="flex-1"
            aria-describedby={validationError ? "tag-validation-error" : undefined}
            aria-invalid={!!validationError}
          />
          <Button type="submit" variant="secondary" size="icon" disabled={!newTag.trim() || tags.length >= TAG_RULES.MAX_COUNT} aria-label="添加标签">
            <Plus className="w-4 h-4" aria-hidden="true" />
          </Button>
        </form>
        {validationError && (
          <div id="tag-validation-error" role="alert" className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" aria-hidden="true" />
            <span>{validationError}</span>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <span id="current-tags-label" className="text-sm font-medium leading-none">
          当前标签 ({tags.length})
        </span>
        <div 
          className="min-h-[3rem] p-3 border rounded-lg bg-background flex flex-wrap gap-2 content-start"
          role="group"
          aria-labelledby="current-tags-label"
        >
          {tags.length === 0 ? (
            <span className="text-sm text-muted-foreground italic">暂无标签</span>
          ) : (
            tags.map(tag => (
              <Badge key={tag} variant="secondary" className="pl-2 pr-1 py-1 flex items-center gap-1">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:bg-muted-foreground/20 rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-ring rounded"
                  aria-label={`移除标签 ${tag}`}
                >
                  <X className="w-3 h-3" aria-hidden="true" />
                </button>
              </Badge>
            ))
          )}
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="outline" onClick={onClose} disabled={saving}>
          取消
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存更改'}
        </Button>
      </div>
    </div>
  );
}

interface TagManageModalProps {
  email: string;
  currentTags?: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

// 外部组件,使用 key 来重置内部状态
export default function TagManageModal({ email, currentTags = [], isOpen, onClose, onSuccess }: TagManageModalProps) {
  if (!isOpen) return null;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="管理标签"
      className="max-w-md"
    >
      <TagManageModalContent
        key={`${email}-${isOpen}`}
        email={email}
        currentTags={currentTags}
        onClose={onClose}
        onSuccess={onSuccess}
      />
    </Dialog>
  );
}
