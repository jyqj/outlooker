import { useId } from 'react';
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
  const listId = useId();

  const handleButtonKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!isOpen) {
        onToggle();
      }
    }
  };

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = e.target as HTMLElement;
      const button = target.closest('button[role="option"]') as HTMLButtonElement;
      if (button) button.click();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const target = e.target as HTMLElement;
      const sibling = e.key === 'ArrowDown'
        ? target.nextElementSibling as HTMLElement
        : target.previousElementSibling as HTMLElement;
      if (sibling?.matches('button[role="option"]')) {
        sibling.focus();
      }
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={onToggle}
        onKeyDown={handleButtonKeyDown}
        className="w-full flex items-center justify-between px-3 py-2 border rounded-md bg-background text-left transition-all duration-150 hover:bg-muted/50 active:scale-[var(--scale-click)] active:bg-muted/70 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listId}
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
          id={listId}
          aria-label="可用标签列表"
          onKeyDown={handleMenuKeyDown}
          className="absolute z-[300] w-full mt-1 py-1 bg-popover border rounded-md shadow-lg max-h-48 overflow-auto"
        >
          {availableTags.map((t) => (
            <button
              key={t}
              type="button"
              role="option"
              aria-selected={value === t}
              onClick={() => onSelect(t)}
              className={`w-full px-3 py-2 text-left transition-colors hover:bg-muted active:bg-muted/80 ${
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
            className="w-full px-3 py-2 text-left transition-colors hover:bg-muted active:bg-muted/80 text-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            输入新标签
          </button>
        </div>
      )}
    </div>
  );
}
