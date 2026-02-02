import type { Email } from '@/types';

/**
 * 邮件分页信息
 */
export interface EmailPagination {
  page: number;
  totalPages: number;
  total: number;
}

/**
 * EmailListView 组件属性
 */
export interface EmailListViewProps {
  /** 邮件列表 */
  messages: Email[];
  /** 当前选中的邮件 ID */
  selectedMessageId: string | null;
  /** 是否正在加载 */
  isLoading: boolean;
  /** 是否加载出错 */
  isError: boolean;
  /** 分页信息 */
  pagination: EmailPagination | null;
  /** 选中邮件的回调 */
  onSelectMessage: (id: string) => void;
  /** 页码变更回调 */
  onPageChange: (page: number) => void;
  /** 刷新回调 */
  onRefresh: () => void;
}

/**
 * EmailDetailView 组件属性
 */
export interface EmailDetailViewProps {
  /** 选中的邮件 */
  message: Email | undefined;
  /** 验证码（已提取） */
  verificationCode: string | null;
  /** 是否正在删除 */
  deleting: boolean;
  /** 删除邮件回调 */
  onDelete: (id: string) => void;
}

/**
 * EmailBody 组件属性
 */
export interface EmailBodyProps {
  /** 邮件正文 */
  body: Email['body'];
}

/**
 * EmailViewModal 组件属性
 */
export interface EmailViewModalProps {
  /** 邮箱地址 */
  email: string;
  /** 是否打开 */
  isOpen: boolean;
  /** 关闭回调 */
  onClose: () => void;
}

/**
 * 消息数据结构（API 响应）
 */
export interface MessagesData {
  items?: Email[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}
