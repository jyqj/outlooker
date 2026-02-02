import { useState, useRef, useEffect } from 'react';
import { Shuffle, Plus, X, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import TagDropdown from './TagDropdown';
import type { PickAccountFormProps } from './types';

/**
 * 取号表单组件
 * 包含标签选择、排除标签、凭证选项等输入项
 */
export default function PickAccountForm({
  effectiveTag,
  isCustomTag,
  customTag,
  tag,
  excludeTags,
  newExcludeTag,
  returnCredentials,
  availableTags,
  loading,
  error,
  onTagChange,
  onCustomTagChange,
  onIsCustomTagChange,
  onExcludeTagsChange,
  onNewExcludeTagChange,
  onReturnCredentialsChange,
  onSubmit,
  onCancel,
}: PickAccountFormProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isDropdownOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isDropdownOpen]);

  // Handle tag selection from dropdown
  const handleTagSelect = (selectedTag: string) => {
    if (selectedTag === '__custom__') {
      onIsCustomTagChange(true);
      onTagChange('');
      onCustomTagChange('');
    } else {
      onIsCustomTagChange(false);
      onTagChange(selectedTag);
    }
    setIsDropdownOpen(false);
  };

  // Add exclude tag
  const handleAddExcludeTag = () => {
    const trimmed = newExcludeTag.trim();
    if (trimmed && !excludeTags.includes(trimmed)) {
      onExcludeTagsChange([...excludeTags, trimmed]);
      onNewExcludeTagChange('');
    }
  };

  // Remove exclude tag
  const handleRemoveExcludeTag = (tagToRemove: string) => {
    onExcludeTagsChange(excludeTags.filter((t) => t !== tagToRemove));
  };

  return (
    <div className="space-y-5 py-2">
      {/* Tag Input */}
      <div className="space-y-2">
        <label htmlFor="target-tag-input" className="text-sm font-medium">
          目标标签 <span className="text-destructive" aria-hidden="true">*</span>
          <span className="sr-only">（必填）</span>
        </label>

        {/* Tag Selection */}
        {!isCustomTag && availableTags.length > 0 ? (
          <TagDropdown
            value={tag}
            availableTags={availableTags}
            isOpen={isDropdownOpen}
            onSelect={handleTagSelect}
            onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
            onClose={() => setIsDropdownOpen(false)}
            dropdownRef={dropdownRef}
          />
        ) : (
          <div className="space-y-2">
            <Input
              id="target-tag-input"
              value={customTag}
              onChange={(e) => onCustomTagChange(e.target.value)}
              placeholder="输入要打的标签，如: 注册-Apple"
              required
              aria-describedby="target-tag-hint"
            />
            {availableTags.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  onIsCustomTagChange(false);
                  onCustomTagChange('');
                }}
                className="text-sm text-primary hover:underline"
              >
                从已有标签选择
              </button>
            )}
          </div>
        )}

        <p id="target-tag-hint" className="text-xs text-muted-foreground">
          系统会随机选择一个没有此标签的账户，并自动打上该标签
        </p>
      </div>

      {/* Exclude Tags */}
      <div className="space-y-2">
        <label htmlFor="exclude-tag-input" className="text-sm font-medium">
          排除标签（可选）
        </label>
        <div className="flex gap-2">
          <Input
            id="exclude-tag-input"
            value={newExcludeTag}
            onChange={(e) => onNewExcludeTagChange(e.target.value)}
            placeholder="输入要排除的标签"
            onKeyDown={(e) =>
              e.key === 'Enter' && (e.preventDefault(), handleAddExcludeTag())
            }
            aria-describedby="exclude-tags-hint"
          />
          <Button
            type="button"
            variant="secondary"
            size="icon"
            onClick={handleAddExcludeTag}
            disabled={!newExcludeTag.trim()}
            aria-label="添加排除标签"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
        {excludeTags.length > 0 && (
          <div
            className="flex flex-wrap gap-1.5 mt-2"
            role="group"
            aria-label="已添加的排除标签"
          >
            {excludeTags.map((t) => (
              <Badge
                key={t}
                variant="secondary"
                className="pl-2 pr-1 py-1 flex items-center gap-1"
              >
                {t}
                <button
                  onClick={() => handleRemoveExcludeTag(t)}
                  className="hover:bg-muted-foreground/20 rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
                  aria-label={`移除排除标签 ${t}`}
                >
                  <X className="w-3 h-3" aria-hidden="true" />
                </button>
              </Badge>
            ))}
          </div>
        )}
        <p id="exclude-tags-hint" className="text-xs text-muted-foreground">
          有这些标签的账户不会被选中
        </p>
      </div>

      {/* Return Credentials Option */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="return-credentials"
          checked={returnCredentials}
          onChange={(e) => onReturnCredentialsChange(e.target.checked)}
          className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
        />
        <label htmlFor="return-credentials" className="text-sm">
          同时返回凭证信息（密码、refresh_token）
        </label>
      </div>

      {/* Error Message */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-lg"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="outline" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button
          onClick={onSubmit}
          disabled={loading || !effectiveTag.trim()}
          className="gap-1"
        >
          {loading ? (
            <>
              <Shuffle className="w-4 h-4 animate-spin" />
              正在取号...
            </>
          ) : (
            <>
              <Shuffle className="w-4 h-4" />
              确认取号
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
