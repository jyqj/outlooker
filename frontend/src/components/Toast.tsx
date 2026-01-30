import React, { useEffect, useState } from 'react';
import { X, CheckCircle, XCircle, Info, AlertTriangle, type LucideIcon } from 'lucide-react';
import type { ToastType, ToastDetail } from '@/lib/toast';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
  duration: number;
}

interface TypeConfig {
  bgColor: string;
  borderColor: string;
  textColor: string;
  iconColor: string;
  Icon: LucideIcon;
}

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
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
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
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-800',
      iconColor: 'text-green-600',
      Icon: CheckCircle,
    },
    error: {
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-800',
      iconColor: 'text-red-600',
      Icon: XCircle,
    },
    info: {
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-800',
      iconColor: 'text-blue-600',
      Icon: Info,
    },
    warning: {
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-800',
      iconColor: 'text-yellow-600',
      Icon: AlertTriangle,
    },
  };

  const config = typeConfig[type] || typeConfig.info;
  const { bgColor, borderColor, textColor, iconColor, Icon } = config;

  return (
    <div
      className={`
        ${bgColor} ${borderColor} ${textColor}
        border rounded-lg shadow-lg p-4 min-w-80 max-w-md
        flex items-start gap-3 pointer-events-auto
        animate-in slide-in-from-right-full duration-300
      `}
    >
      <Icon className={`w-5 h-5 ${iconColor} flex-shrink-0 mt-0.5`} />
      <p className="flex-1 text-sm font-medium">{message}</p>
      <button
        onClick={onClose}
        className="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
        aria-label="关闭"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default ToastContainer;
