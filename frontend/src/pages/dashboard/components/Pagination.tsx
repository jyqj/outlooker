import type { KeyboardEvent } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface PaginationProps {
  page: number;
  pageSize: number;
  totalPages: number;
  totalRecords: number;
  jumpToPage: string;
  pageNumbers: (number | string)[];
  isFirstPage: boolean;
  isLastPage: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: string) => void;
  onJumpToPageChange: (value: string) => void;
  onJumpToPage: () => void;
  onNextPage: () => void;
  onPrevPage: () => void;
}

export function Pagination({
  page,
  pageSize,
  totalPages,
  totalRecords,
  jumpToPage,
  pageNumbers,
  isFirstPage,
  isLastPage,
  onPageChange,
  onPageSizeChange,
  onJumpToPageChange,
  onJumpToPage,
  onNextPage,
  onPrevPage,
}: PaginationProps) {
  return (
    <div className="border-t px-4 md:px-6 py-4 bg-muted/40">
      {/* Mobile Layout */}
      <div className="flex md:hidden flex-col gap-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            共 {totalRecords} 条
          </p>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(e.target.value)}
            className="text-xs border rounded px-2 py-1 bg-background"
          >
            <option value="10">10条/页</option>
            <option value="20">20条/页</option>
            <option value="50">50条/页</option>
            <option value="100">100条/页</option>
          </select>
        </div>
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={onPrevPage}
            disabled={isFirstPage}
            className="gap-1"
          >
            <ChevronLeft className="w-3 h-3" />
            上一页
          </Button>
          <span className="text-sm font-medium">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onNextPage}
            disabled={isLastPage}
            className="gap-1"
          >
            下一页
            <ChevronRight className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Desktop Layout */}
      <div className="hidden md:flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <p className="text-sm text-muted-foreground whitespace-nowrap">
            共 {totalRecords} 条记录
          </p>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(e.target.value)}
            className="text-sm border rounded-md px-3 py-1.5 bg-background focus:ring-2 focus:ring-ring outline-none"
          >
            <option value="10">10 条/页</option>
            <option value="20">20 条/页</option>
            <option value="50">50 条/页</option>
            <option value="100">100 条/页</option>
          </select>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={onPrevPage}
            disabled={isFirstPage}
            className="h-9 w-9"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          {pageNumbers.map((pageNum, idx) => (
            pageNum === '...' ? (
              <span key={`ellipsis-${idx}`} className="px-2 text-muted-foreground">
                ...
              </span>
            ) : (
              <Button
                key={pageNum}
                variant={page === pageNum ? 'default' : 'outline'}
                size="icon"
                onClick={() => onPageChange(pageNum as number)}
                className="h-9 w-9"
              >
                {pageNum}
              </Button>
            )
          ))}

          <Button
            variant="outline"
            size="icon"
            onClick={onNextPage}
            disabled={isLastPage}
            className="h-9 w-9"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground whitespace-nowrap">跳转到</span>
          <Input
            type="text"
            value={jumpToPage}
            onChange={(e) => onJumpToPageChange(e.target.value)}
            onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
              if (e.key === 'Enter') {
                onJumpToPage();
              }
            }}
            placeholder="页码"
            className="w-16 h-9 text-center text-sm"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={onJumpToPage}
            disabled={!jumpToPage}
            className="h-9"
          >
            跳转
          </Button>
        </div>
      </div>
    </div>
  );
}
