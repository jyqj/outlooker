/**
 * Toast 通知工具
 * 使用 CustomEvent 发送通知，由 ToastContainer 组件监听
 */

export function showToast(message, type = 'info', duration = 3000) {
  const event = new CustomEvent('showToast', {
    detail: { message, type, duration },
  });
  window.dispatchEvent(event);
}

export function showSuccess(message, duration = 3000) {
  showToast(message, 'success', duration);
}

export function showError(message, duration = 3000) {
  showToast(message, 'error', duration);
}

export function showInfo(message, duration = 3000) {
  showToast(message, 'info', duration);
}

