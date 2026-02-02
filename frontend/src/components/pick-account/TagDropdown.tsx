import { ChevronDown, Plus } from 'lucide-react';
import type { TagDropdownProps } from './types';

/**
 * 标签下拉选择组件
 * 用于选择已有标签或输入新标签
 */
export default function TagDropdown({
  value,
  availableTags,
  isOpen,
  onSelect,
  onToggle,
  onClose,
  dropdownRef,
}: TagDropdownProps) {
  // Handle keyboard navigation for dropdown button
  const handleButtonKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) {
        onToggle();
      }
    }
  };

  // Handle keyboard navigation for dropdown menu
  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = e.target as HTMLElement;
      const button = target.closest('button[role="option"]') as HTMLButtonElement;
      if (button) {
        button.click();
      }
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={onToggle}
        onKeyDown={handleButtonKeyDown}
        className="w-full flex items-center justify-between px-3 py-2 border rounded-md bg-background hover:bg-muted/50 transition-colors text-left"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls="tag-dropdown-list"
        aria-label="选择目标标签"
      >
        <span className={value ? 'text-foreground' : 'text-muted-foreground'}>
          {value || '选择已有标签...'}
        </span>
        <ChevronDown 
          className={`w-4 h-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {isOpen && (
        <div
          role="listbox"
          id="tag-dropdown-list"
          aria-label="可用标签列表"
          onKeyDown={handleMenuKeyDown}
          className="absolute z-50 w-full mt-1 py-1 bg-popover border rounded-md shadow-lg max-h-48 overflow-auto"
        >
          {availableTags.map((t) => (
            <button
              key={t}
              type="button"
              role="option"
              aria-selected={value === t}
              onClick={() => onSelect(t)}
              className={`w-full px-3 py-2 text-left hover:bg-muted transition-colors ${
                value === t ? 'bg-muted font-medium' : ''
              }`}
            >
              {t}
            </button>
          ))}
          <div className="border-t my-1" />
          <button
            type="button"
            role="option"
            aria-selected={false}
            onClick={() => onSelect('__custom__')}
            className="w-full px-3 py-2 text-left hover:bg-muted transition-colors text-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            输入新标签
          </button>
        </div>
      )}
    </div>
  );
}
