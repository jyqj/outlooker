import React, { useEffect, useState } from 'react';
import { X, CheckCircle, XCircle, Info, AlertTriangle, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToastType, ToastDetail } from '@/lib/toast';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
  duration: number;
}

interface TypeConfig {
  variant: string;
  iconClass: string;
  Icon: LucideIcon;
}

const toastVariants: Record<ToastType, string> = {
  success: "bg-success/10 border-success/20 text-success",
  error: "bg-destructive/10 border-destructive/20 text-destructive",
  warning: "bg-warning/10 border-warning/20 text-warning-foreground",
  info: "bg-info/10 border-info/20 text-info",
};

const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handleShowToast = (event: Event) => {
      const customEvent = event as CustomEvent<ToastDetail>;
      const { message, type = 'info', duration = 3000 } = customEvent.detail;
      const id = Date.now() + Math.random();

      const newToast: Toast = { id, message, type, duration };
      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((toast) => toast.id !== id));
        }, duration);
      }
    };

    window.addEventListener('showToast', handleShowToast);
    return () => window.removeEventListener('showToast', handleShowToast);
  }, []);

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <div
      className="fixed top-16 right-4 z-50 flex flex-col gap-2 pointer-events-none"
      role="status"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
};

interface ToastItemProps {
  toast: Toast;
  onClose: () => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onClose }) => {
  const { message, type } = toast;

  const typeConfig: Record<ToastType, TypeConfig> = {
    success: {
      variant: toastVariants.success,
      iconClass: 'text-success',
      Icon: CheckCircle,
    },
    error: {
      variant: toastVariants.error,
      iconClass: 'text-destructive',
      Icon: XCircle,
    },
    info: {
      variant: toastVariants.info,
      iconClass: 'text-info',
      Icon: Info,
    },
    warning: {
      variant: toastVariants.warning,
      iconClass: 'text-warning-foreground',
      Icon: AlertTriangle,
    },
  };

  const config = typeConfig[type] || typeConfig.info;
  const { variant, iconClass, Icon } = config;

  return (
    <div
      className={cn(
        "border rounded-lg shadow-lg p-4 min-w-80 max-w-md",
        "flex items-start gap-3 pointer-events-auto",
        "animate-in slide-in-from-right-full duration-300",
        variant
      )}
    >
      <Icon className={cn("w-5 h-5 flex-shrink-0 mt-0.5", iconClass)} />
      <p className="flex-1 text-sm font-medium">{message}</p>
      <button
        onClick={onClose}
        className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
        aria-label="关闭"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default ToastContainer;
