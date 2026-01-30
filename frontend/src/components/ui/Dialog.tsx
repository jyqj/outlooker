import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

export interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children?: React.ReactNode
  className?: string
}

const Dialog: React.FC<DialogProps> = ({ isOpen, onClose, title, children, className }) => {
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const contentRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        ref={overlayRef}
        className="fixed inset-0 bg-black/70 backdrop-blur-md transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Content */}
      <div
        ref={contentRef}
        className={cn(
          "relative z-50 grid w-full max-w-lg scale-100 gap-4 bg-white dark:bg-gray-950 p-6 shadow-2xl duration-200 animate-in fade-in-0 zoom-in-95 sm:rounded-lg md:w-full",
          className
        )}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex flex-col space-y-1.5 text-center sm:text-left">
          {title && (
            <h2 className="text-lg font-semibold leading-none tracking-tight">
              {title}
            </h2>
          )}
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </button>
        </div>
        
        {children}
      </div>
    </div>
  )
}

export { Dialog }
