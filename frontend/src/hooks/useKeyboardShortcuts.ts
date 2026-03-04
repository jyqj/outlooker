import { useEffect } from 'react';

interface ShortcutMap {
  [key: string]: () => void;
}

export function useKeyboardShortcuts(shortcuts: ShortcutMap) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      if (e.key === 'Escape') {
        shortcuts['Escape']?.();
        return;
      }

      if (mod && e.key === 'k') {
        e.preventDefault();
        shortcuts['mod+k']?.();
        return;
      }

      if (mod && e.key === 'Enter' && !isInput) {
        e.preventDefault();
        shortcuts['mod+Enter']?.();
        return;
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [shortcuts]);
}
