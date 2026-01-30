import { useState, useCallback, useRef, useEffect } from 'react';

export interface AccountSelectionState {
  selectedAccounts: Set<string>;
  toggleSelectAccount: (email: string) => void;
  toggleSelectAll: () => void;
  clearSelection: () => void;
  isAllSelected: boolean;
  selectedCount: number;
}

/**
 * 账户选择状态管理 Hook
 * 处理单选、全选、取消选择等操作
 */
export function useAccountSelection(accountEmails: string[] = []): AccountSelectionState {
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  
  // Use ref to avoid stale closure while optimizing dependency array
  const accountEmailsRef = useRef(accountEmails);
  useEffect(() => {
    accountEmailsRef.current = accountEmails;
  }, [accountEmails]);

  const toggleSelectAccount = useCallback((email: string) => {
    setSelectedAccounts(prev => {
      const next = new Set(prev);
      if (next.has(email)) {
        next.delete(email);
      } else {
        next.add(email);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    const emails = accountEmailsRef.current;
    if (selectedAccounts.size === emails.length && emails.length > 0) {
      setSelectedAccounts(new Set());
    } else {
      setSelectedAccounts(new Set(emails));
    }
  }, [selectedAccounts.size]);

  const clearSelection = useCallback(() => {
    setSelectedAccounts(new Set());
  }, []);

  const isAllSelected = accountEmails.length > 0 && selectedAccounts.size === accountEmails.length;

  return {
    selectedAccounts,
    toggleSelectAccount,
    toggleSelectAll,
    clearSelection,
    isAllSelected,
    selectedCount: selectedAccounts.size,
  };
}
