import { Tags, ArrowLeft, RefreshCw, Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { TagsPageHeaderProps } from './types';

export function TagsPageHeader({ 
  isLoading, 
  onRefresh, 
  onRandomPick, 
  onBack 
}: TagsPageHeaderProps) {
  return (
    <header className="bg-background border-b px-6 py-4 flex justify-between items-center sticky top-0 z-20 shadow-sm [background:hsl(var(--background))]">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="gap-1"
        >
          <ArrowLeft className="w-4 h-4" />
          返回
        </Button>
        <div className="h-6 w-px bg-border" />
        <div className="bg-primary p-2 rounded-lg text-primary-foreground">
          <Tags className="w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold tracking-tight">标签管理</h1>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isLoading}
          className="gap-1"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
        <Button
          variant="default"
          size="sm"
          onClick={onRandomPick}
          className="gap-1"
        >
          <Plus className="w-4 h-4" />
          随机取号
        </Button>
      </div>
    </header>
  );
}
