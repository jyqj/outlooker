import { useState, useCallback } from 'react';

interface ModalState<T = undefined> {
  isOpen: boolean;
  data: T | undefined;
}

export function useModalState<T = undefined>(initialData?: T) {
  const [state, setState] = useState<ModalState<T>>({
    isOpen: false,
    data: initialData,
  });

  const open = useCallback((data?: T) => {
    setState({ isOpen: true, data });
  }, []);

  const close = useCallback(() => {
    setState(prev => ({ ...prev, isOpen: false }));
  }, []);

  const setData = useCallback((data: T | undefined) => {
    setState(prev => ({ ...prev, data }));
  }, []);

  return {
    isOpen: state.isOpen,
    data: state.data,
    open,
    close,
    setData,
  };
}
