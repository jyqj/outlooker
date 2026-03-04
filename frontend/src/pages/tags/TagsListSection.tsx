import React from 'react';
import { useTranslation } from 'react-i18next';
import { Tags, Shuffle, Eye, Pencil, Trash2, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { TagStatItem } from '@/types';
import type { TagsListSectionProps } from './types';

interface TagListItemProps {
  tag: TagStatItem;
  onPick: (tagName: string) => void;
  onView: (tagName: string) => void;
  onDelete: (tagName: string) => void;
  onRename: (tagName: string) => void;
  isLoading: boolean;
}

const TagListItem = React.memo(function TagListItem({ 
  tag, 
  onPick, 
  onView,
  onDelete,
  onRename,
  isLoading 
}: TagListItemProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-between p-4 border-b last:border-b-0 hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="px-3 py-1">
          {tag.name}
        </Badge>
        <span className="text-sm text-muted-foreground">
          {t('tags.accountCountWithPercent', { count: tag.count, percent: tag.percentage })}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPick(tag.name)}
          disabled={isLoading}
          className="gap-1"
        >
          <Shuffle className="w-3.5 h-3.5" />
          {t('tags.pick')}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(tag.name)}
          className="gap-1"
        >
          <Eye className="w-3.5 h-3.5" />
          {t('tags.view')}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRename(tag.name)}
          disabled={isLoading}
          className="gap-1 text-muted-foreground hover:text-foreground"
        >
          <Pencil className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(tag.name)}
          disabled={isLoading}
          className="gap-1 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
});

TagListItem.displayName = 'TagListItem';

export function TagsListSection({ 
  tags, 
  isLoading, 
  onPick, 
  onView, 
  onDelete, 
  onRename 
}: TagsListSectionProps) {
  const { t } = useTranslation();
  return (
    <Card>
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-muted-foreground" />
          <h2 className="font-semibold">{t('tags.listTitle')}</h2>
          <Badge variant="outline">{t('tags.tagCount', { count: tags.length })}</Badge>
        </div>
      </div>
      
      {tags.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground">
          <Tags className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>{t('tags.noTags')}</p>
          <p className="text-sm mt-1">{t('tags.noTagsHint')}</p>
        </div>
      ) : (
        <div>
          {tags.map((tag) => (
            <TagListItem
              key={tag.name}
              tag={tag}
              onPick={onPick}
              onView={onView}
              onDelete={onDelete}
              onRename={onRename}
              isLoading={isLoading}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
