import { useState } from 'react';

export function useDashboardModals() {
  const [showImport, setShowImport] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);
  const [tagModal, setTagModal] = useState<{ isOpen: boolean; email: string | null }>({ isOpen: false, email: null });
  const [exporting, setExporting] = useState(false);

  const openImport = () => setShowImport(true);
  const closeImport = () => setShowImport(false);
  
  const openEmailView = (email: string) => setSelectedEmail(email);
  const closeEmailView = () => setSelectedEmail(null);

  const openTagManage = (email: string) => setTagModal({ isOpen: true, email });
  const closeTagManage = () => setTagModal({ isOpen: false, email: null });

  return {
    showImport,
    openImport,
    closeImport,
    selectedEmail,
    openEmailView,
    closeEmailView,
    tagModal,
    openTagManage,
    closeTagManage,
    exporting,
    setExporting
  };
}
