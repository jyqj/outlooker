/**
 * Hooks 统一入口
 * 重新导出所有通用 hooks，便于统一管理和导入
 */

// 从 lib/hooks.ts 重新导出通用 hooks（保持兼容性）
export * from '../lib/hooks';

// 通用工具 hooks
export { useCopyToClipboard } from './useCopyToClipboard';
export { useModalState } from './useModalState';

// 页面级 hooks
export { useVerification } from './useVerification';
