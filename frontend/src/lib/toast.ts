/**
 * Toast 通知工具
 * 使用 CustomEvent 发送通知，由 ToastContainer 组件监听
 */

export type ToastType = 'info' | 'success' | 'error' | 'warning';

export interface ToastDetail {
  message: string;
  type: ToastType;
  duration: number;
}

export function showToast(message: string, type: ToastType = 'info', duration: number = 3000): void {
  const event = new CustomEvent<ToastDetail>('showToast', {
    detail: { message, type, duration },
  });
  window.dispatchEvent(event);
}

export function showSuccess(message: string, duration: number = 3000): void {
  showToast(message, 'success', duration);
}

export function showError(message: string, duration: number = 3000): void {
  showToast(message, 'error', duration);
}

export function showInfo(message: string, duration: number = 3000): void {
  showToast(message, 'info', duration);
}

export function showWarning(message: string, duration: number = 3000): void {
  showToast(message, 'warning', duration);
}
