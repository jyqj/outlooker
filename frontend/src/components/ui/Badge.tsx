import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

import type { BadgeVariant } from "@/types/components"

export type { BadgeVariant }

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 active:scale-[var(--scale-click-sm)]",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80 active:bg-primary/70",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80 active:bg-secondary/70",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80 active:bg-destructive/70",
        outline: "text-foreground active:bg-muted/50",
        success: "border-transparent bg-success text-success-foreground hover:bg-success/80 active:bg-success/70",
        warning: "border-transparent bg-warning text-warning-foreground hover:bg-warning/80 active:bg-warning/70",
        info: "border-transparent bg-info text-info-foreground hover:bg-info/80 active:bg-info/70",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    )
  }
)
Badge.displayName = "Badge"

export { Badge, badgeVariants }
