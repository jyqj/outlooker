import type { TagStatItem } from '@/types';

export interface TagDeleteDialogProps {
  isOpen: boolean;
  tagName: string;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface TagRenameDialogProps {
  isOpen: boolean;
  oldName: string;
  newName: string;
  loading: boolean;
  onNewNameChange: (value: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface TagsStatsProps {
  totalAccounts: number;
  taggedAccounts: number;
  untaggedAccounts: number;
}

export interface TagListItemData {
  name: string;
  count: number;
  percentage: string;
}

export interface TagsListSectionProps {
  tags: TagStatItem[];
  isLoading: boolean;
  onPick: (tagName: string) => void;
  onView: (tagName: string) => void;
  onDelete: (tagName: string) => void;
  onRename: (tagName: string) => void;
}

export interface UntaggedAccountsCardProps {
  count: number;
  onView: () => void;
}

export interface TagsPageHeaderProps {
  isLoading: boolean;
  onRefresh: () => void;
  onRandomPick: () => void;
  onBack: () => void;
}

export interface PickModalState {
  isOpen: boolean;
  preselectedTag: string;
}

export interface DeleteDialogState {
  isOpen: boolean;
  tagName: string;
  loading: boolean;
}

export interface RenameDialogState {
  isOpen: boolean;
  oldName: string;
  newName: string;
  loading: boolean;
}
