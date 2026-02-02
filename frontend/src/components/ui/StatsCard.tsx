import * as React from 'react';
import { Card } from './Card';
import { cn } from '@/lib/utils';

export interface StatsCardProps {
  /** Card title displayed above the value */
  title: string;
  /** Main value to display (can be number or formatted string) */
  value: string | number;
  /** Optional description text below the value */
  description?: string;
  /** Optional icon element to display */
  icon?: React.ReactNode;
  /** Optional trend indicator */
  trend?: {
    value: number;
    label: string;
    isPositive?: boolean;
  };
  /** Color variant for the icon background */
  color?: 'primary' | 'success' | 'warning' | 'muted' | 'destructive';
  /** Additional CSS classes */
  className?: string;
}

const colorClasses = {
  primary: 'bg-primary/10 text-primary',
  success: 'bg-green-500/10 text-green-600 dark:text-green-400',
  warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  muted: 'bg-muted text-muted-foreground',
  destructive: 'bg-destructive/10 text-destructive',
};

export const StatsCard = React.forwardRef<HTMLDivElement, StatsCardProps>(
  ({ title, value, description, icon, trend, color = 'primary', className }, ref) => {
    return (
      <Card ref={ref} className={cn('p-4', className)}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1">
            {icon && (
              <div className={cn('p-2 rounded-lg flex-shrink-0', colorClasses[color])}>
                {icon}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground truncate">
                {title}
              </p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                {value}
              </p>
              {description && (
                <p className="mt-1 text-sm text-muted-foreground truncate">
                  {description}
                </p>
              )}
              {trend && (
                <div
                  className={cn(
                    'mt-2 flex items-center text-sm',
                    trend.isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  )}
                  role="status"
                  aria-label={`趋势: ${trend.isPositive ? '上升' : '下降'} ${Math.abs(trend.value)}% ${trend.label}`}
                >
                  <span aria-hidden="true">
                    {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
                  </span>
                  <span className="ml-1 text-muted-foreground">{trend.label}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>
    );
  }
);

StatsCard.displayName = 'StatsCard';

export default StatsCard;
