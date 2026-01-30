import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LoadingSpinnerProps {
  /** 显示文本 */
  text?: string;
  /** 副标题文本 */
  subText?: string;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** 额外的 className */
  className?: string;
  /** 是否显示外圈装饰 */
  showRing?: boolean;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
};

const ringSizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-3',
  lg: 'w-12 h-12 border-4',
  xl: 'w-16 h-16 border-4',
};

const textSizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-lg',
};

/**
 * 通用加载指示器组件
 */
export function LoadingSpinner({
  text,
  subText,
  size = 'md',
  className,
  showRing = false,
}: LoadingSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-4', className)}>
      <div className="relative">
        <Loader2 className={cn('text-primary animate-spin', sizeClasses[size])} />
        {showRing && (
          <div 
            className={cn(
              'absolute inset-0 border-primary/20 rounded-full',
              ringSizeClasses[size]
            )} 
          />
        )}
      </div>
      {(text || subText) && (
        <div className="text-center space-y-1">
          {text && (
            <p className={cn('font-semibold text-foreground', textSizeClasses[size])}>
              {text}
            </p>
          )}
          {subText && (
            <p className="text-sm text-muted-foreground">{subText}</p>
          )}
        </div>
      )}
    </div>
  );
}
