import { CheckSquare, Square, Mail, Tag } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { Account } from '@/types';

interface AccountTableRowProps {
  account: Account;
  isSelected: boolean;
  tags: string[];
  onToggleSelect: (email: string) => void;
  onViewEmails: (email: string) => void;
  onManageTags: (email: string) => void;
}

export function AccountTableRow({
  account,
  isSelected,
  tags,
  onToggleSelect,
  onViewEmails,
  onManageTags,
}: AccountTableRowProps) {
  const isUsed = typeof account.is_used === 'boolean' ? account.is_used : null;
  const lastUsedAt = account.last_used_at;

  return (
    <tr 
      className={`hover:bg-muted/80 transition-colors ${isSelected ? 'bg-primary/5' : ''}`}
      role="row"
      aria-selected={isSelected}
    >
      <td className="px-4 py-4" role="gridcell">
        <button
          onClick={() => onToggleSelect(account.email)}
          className="p-1 hover:bg-muted-foreground/10 rounded focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label={isSelected ? `取消选择 ${account.email}` : `选择 ${account.email}`}
          aria-pressed={isSelected}
          type="button"
        >
          {isSelected ? (
            <CheckSquare className="w-4 h-4 text-primary" aria-hidden="true" />
          ) : (
            <Square className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
          )}
        </button>
      </td>
      <td className="px-4 py-4 font-medium" role="gridcell">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span>{account.email}</span>
            {isUsed !== null && (
              <Badge
                variant={isUsed ? 'outline' : 'secondary'}
                className="text-[11px] px-2 py-0.5 rounded-full"
                aria-label={isUsed ? '已使用' : '未使用'}
              >
                {isUsed ? '已使用(公共池)' : '未使用(公共池)'}
              </Badge>
            )}
          </div>
          {isUsed && lastUsedAt && (
            <span className="text-xs text-muted-foreground">
              最后使用：{lastUsedAt}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-4" role="gridcell">
        <div className="flex gap-1 flex-wrap" role="list" aria-label="账户标签">
          {tags.map(tag => (
            <Badge key={tag} variant="secondary" className="text-xs" role="listitem">
              {tag}
            </Badge>
          ))}
          {tags.length === 0 && (
            <span className="text-muted-foreground italic text-xs">无标签</span>
          )}
        </div>
      </td>
      <td className="px-4 py-4 text-right" role="gridcell">
        <div className="flex gap-2 justify-end" role="group" aria-label="账户操作">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onViewEmails(account.email)}
            className="h-8 w-8 text-muted-foreground hover:text-primary"
            title="查看邮件"
            aria-label={`查看 ${account.email} 的邮件`}
          >
            <Mail className="w-4 h-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-green-600"
            title="管理标签"
            aria-label={`管理 ${account.email} 的标签`}
            onClick={() => onManageTags(account.email)}
          >
            <Tag className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>
      </td>
    </tr>
  );
}
