/**
 * 取号结果数据结构
 */
export interface PickResult {
  email: string;
  tags: string[];
  password?: string;
  refresh_token?: string;
  client_id?: string;
}

/**
 * Modal 步骤类型
 */
export type ModalStep = 'input' | 'result';

/**
 * PickAccountModal 的 Props
 */
export interface PickAccountModalProps {
  isOpen: boolean;
  preselectedTag?: string;
  availableTags?: string[];
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * 表单组件 Props
 */
export interface PickAccountFormProps {
  effectiveTag: string;
  isCustomTag: boolean;
  customTag: string;
  tag: string;
  excludeTags: string[];
  newExcludeTag: string;
  returnCredentials: boolean;
  availableTags: string[];
  loading: boolean;
  error: string | null;
  onTagChange: (tag: string) => void;
  onCustomTagChange: (customTag: string) => void;
  onIsCustomTagChange: (isCustom: boolean) => void;
  onExcludeTagsChange: (tags: string[]) => void;
  onNewExcludeTagChange: (tag: string) => void;
  onReturnCredentialsChange: (value: boolean) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/**
 * 结果展示组件 Props
 */
export interface PickAccountResultProps {
  result: PickResult;
  returnCredentials: boolean;
  onPickAnother: () => void;
  onClose: () => void;
}

/**
 * 凭证展示组件 Props
 */
export interface CredentialsDisplayProps {
  result: PickResult;
  showCredentials: boolean;
  onToggleShow: () => void;
}

/**
 * 标签下拉组件 Props
 */
export interface TagDropdownProps {
  value: string;
  availableTags: string[];
  isOpen: boolean;
  onSelect: (tag: string) => void;
  onToggle: () => void;
  onClose: () => void;
  dropdownRef: React.RefObject<HTMLDivElement | null>;
}
