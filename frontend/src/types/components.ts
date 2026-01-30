/**
 * Shared UI type definitions
 *
 * 约定：
 * - 组件自身的 Props：就近定义在组件文件中，并通过 `src/components/ui/index.ts` 导出。
 * - 跨组件复用的 union/variant 类型：集中放在这里，避免在多个组件里重复声明。
 */

export type ButtonVariant = 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
export type ButtonSize = 'default' | 'sm' | 'lg' | 'icon';

export type AlertVariant = 'default' | 'destructive' | 'success' | 'warning' | 'info';

export type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline';
