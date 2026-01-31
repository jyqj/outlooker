import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const spinnerVariants = cva(
  'text-primary animate-spin',
  {
    variants: {
      size: {
        sm: 'w-4 h-4',
        md: 'w-8 h-8',
        lg: 'w-12 h-12',
        xl: 'w-16 h-16',
      },
    },
    defaultVariants: { size: 'md' },
  }
);

const ringVariants = cva(
  'absolute inset-0 border-primary/20 rounded-full',
  {
    variants: {
      size: {
        sm: 'w-4 h-4 border-2',
        md: 'w-8 h-8 border-[3px]',
        lg: 'w-12 h-12 border-4',
        xl: 'w-16 h-16 border-4',
      },
    },
    defaultVariants: { size: 'md' },
  }
);

const textVariants = cva(
  'font-semibold text-foreground',
  {
    variants: {
      size: {
        sm: 'text-sm',
        md: 'text-base',
        lg: 'text-lg',
        xl: 'text-lg',
      },
    },
    defaultVariants: { size: 'md' },
  }
);

export interface LoadingSpinnerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof spinnerVariants> {
  /** 显示文本 */
  text?: string;
  /** 副标题文本 */
  subText?: string;
  /** 是否显示外圈装饰 */
  showRing?: boolean;
}

/**
 * 通用加载指示器组件
 */
const LoadingSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ text, subText, size, className, showRing = false, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('flex flex-col items-center justify-center gap-4', className)}
        role="status"
        aria-label={text || '加载中'}
        {...props}
      >
        <div className="relative">
          <Loader2 className={cn(spinnerVariants({ size }))} />
          {showRing && (
            <div className={cn(ringVariants({ size }))} />
          )}
        </div>
        {(text || subText) && (
          <div className="text-center space-y-1">
            {text && (
              <p className={cn(textVariants({ size }))}>
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
);
LoadingSpinner.displayName = 'LoadingSpinner';

export { LoadingSpinner, spinnerVariants };
