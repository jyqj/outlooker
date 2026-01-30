import * as React from "react"
import { cn } from "@/lib/utils"

import type { AlertVariant } from "@/types/components"

export type { AlertVariant }

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant
}

const variantStyles: Record<AlertVariant, string> = {
  default: "bg-gray-50 text-gray-900 border-gray-200",
  destructive: "bg-red-50 text-red-900 border-red-200",
  success: "bg-green-50 text-green-900 border-green-200",
  warning: "bg-yellow-50 text-yellow-900 border-yellow-200",
  info: "bg-blue-50 text-blue-900 border-blue-200",
}

export function Alert({ children, variant = "default", className, ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        "relative w-full rounded-lg border p-4",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export interface AlertDescriptionProps extends React.HTMLAttributes<HTMLDivElement> {}

export function AlertDescription({ children, className, ...props }: AlertDescriptionProps) {
  return (
    <div
      className={cn("text-sm [&_p]:leading-relaxed", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export interface AlertTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export function AlertTitle({ children, className, ...props }: AlertTitleProps) {
  return (
    <h5
      className={cn("mb-1 font-medium leading-none tracking-tight", className)}
      {...props}
    >
      {children}
    </h5>
  )
}
