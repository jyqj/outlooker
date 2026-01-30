import { useState, useCallback, useMemo } from 'react';

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  totalRecords: number;
  onError?: (message: string) => void;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  totalPages: number;
  totalRecords: number;
  jumpToPage: string;
  pageNumbers: (number | string)[];
  isFirstPage: boolean;
  isLastPage: boolean;
  setJumpToPage: (value: string) => void;
  setPage: (page: number) => void;
  handlePageSizeChange: (newSize: string | number) => void;
  handleJumpToPage: () => void;
  goToPage: (pageNum: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  resetPage: () => void;
}

/**
 * 分页状态管理 Hook
 */
export function usePagination({
  initialPage = 1,
  initialPageSize = 10,
  totalRecords,
  onError,
}: UsePaginationOptions): PaginationState {
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [jumpToPage, setJumpToPage] = useState('');

  const totalPages = useMemo(() => 
    Math.max(1, Math.ceil(totalRecords / pageSize)),
    [totalRecords, pageSize]
  );

  const handlePageSizeChange = useCallback((newSize: string | number) => {
    setPageSize(Number(newSize));
    setPage(1);
  }, []);

  const handleJumpToPage = useCallback(() => {
    const cleanedInput = jumpToPage.replace(/\D/g, '');
    const pageNum = parseInt(cleanedInput, 10);

    if (isNaN(pageNum) || cleanedInput === '') {
      onError?.('请输入有效的页码');
      return;
    }

    if (pageNum >= 1 && pageNum <= totalPages) {
      setPage(pageNum);
      setJumpToPage('');
    } else {
      onError?.(`请输入 1 到 ${totalPages} 之间的页码`);
    }
  }, [jumpToPage, onError, totalPages]);

  const goToPage = useCallback((pageNum: number) => {
    setPage(Math.max(1, Math.min(pageNum, totalPages)));
  }, [totalPages]);

  const nextPage = useCallback(() => {
    setPage(p => Math.min(totalPages, p + 1));
  }, [totalPages]);

  const prevPage = useCallback(() => {
    setPage(p => Math.max(1, p - 1));
  }, []);

  const resetPage = useCallback(() => {
    setPage(1);
  }, []);

  // Generate page numbers with ellipsis
  const pageNumbers = useMemo((): (number | string)[] => {
    const pages: (number | string)[] = [];
    const showEllipsisStart = page > 3;
    const showEllipsisEnd = page < totalPages - 2;

    pages.push(1);

    if (showEllipsisStart) {
      pages.push('...');
      for (let i = Math.max(2, page - 1); i < page; i++) {
        pages.push(i);
      }
    } else {
      for (let i = 2; i < page; i++) {
        pages.push(i);
      }
    }

    if (page !== 1 && page !== totalPages) {
      pages.push(page);
    }

    if (showEllipsisEnd) {
      for (let i = page + 1; i <= Math.min(page + 1, totalPages - 1); i++) {
        pages.push(i);
      }
      pages.push('...');
    } else {
      for (let i = page + 1; i < totalPages; i++) {
        pages.push(i);
      }
    }

    if (totalPages > 1) {
      pages.push(totalPages);
    }

    return pages;
  }, [page, totalPages]);

  return {
    page,
    pageSize,
    totalPages,
    totalRecords,
    jumpToPage,
    pageNumbers,
    setJumpToPage,
    setPage,
    handlePageSizeChange,
    handleJumpToPage,
    goToPage,
    nextPage,
    prevPage,
    resetPage,
    isFirstPage: page === 1,
    isLastPage: page >= totalPages,
  };
}
