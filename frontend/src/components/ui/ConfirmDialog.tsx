import * as React from "react"
import { AlertTriangle, Info } from "lucide-react"
import { Dialog } from "./Dialog"
import { Button } from "./Button"
import { cn } from "@/lib/utils"

export type ConfirmDialogVariant = 'danger' | 'warning' | 'info';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmDialogVariant;
  loading?: boolean;
}

const variantConfig = {
  danger: {
    icon: AlertTriangle,
    iconClassName: 'text-destructive',
    buttonVariant: 'destructive' as const,
  },
  warning: {
    icon: AlertTriangle,
    iconClassName: 'text-yellow-500',
    buttonVariant: 'default' as const,
  },
  info: {
    icon: Info,
    iconClassName: 'text-blue-500',
    buttonVariant: 'default' as const,
  },
};

/**
 * 确认对话框组件
 * 用于替代原生 confirm()，提供更好的用户体验和可访问性
 */
export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'danger',
  loading = false,
}: ConfirmDialogProps) {
  const confirmButtonRef = React.useRef<HTMLButtonElement>(null);
  const config = variantConfig[variant];
  const Icon = config.icon;

  // 自动聚焦到确认按钮
  React.useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      confirmButtonRef.current.focus();
    }
  }, [isOpen]);

  const handleConfirm = () => {
    onConfirm();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      e.preventDefault();
      handleConfirm();
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-md"
    >
      <div 
        className="flex flex-col items-center text-center p-4"
        onKeyDown={handleKeyDown}
        role="alertdialog"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <div className={cn("w-12 h-12 rounded-full flex items-center justify-center mb-4", 
          variant === 'danger' && "bg-destructive/10",
          variant === 'warning' && "bg-yellow-500/10",
          variant === 'info' && "bg-blue-500/10"
        )}>
          <Icon className={cn("w-6 h-6", config.iconClassName)} aria-hidden="true" />
        </div>
        
        <h3 id="confirm-dialog-title" className="text-lg font-semibold mb-2">
          {title}
        </h3>
        
        <p id="confirm-dialog-description" className="text-muted-foreground text-sm mb-6">
          {message}
        </p>

        <div className="flex gap-3 w-full">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={loading}
            className="flex-1"
            type="button"
          >
            {cancelText}
          </Button>
          <Button
            ref={confirmButtonRef}
            variant={config.buttonVariant}
            onClick={handleConfirm}
            disabled={loading}
            className="flex-1"
            type="button"
          >
            {loading ? '处理中...' : confirmText}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
