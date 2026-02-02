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

// Get all focusable elements within a container
const getFocusableElements = (container: HTMLElement): HTMLElement[] => {
  const elements = container.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  return Array.from(elements).filter(
    el => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true'
  )
}

const Dialog: React.FC<DialogProps> = ({ isOpen, onClose, title, children, className }) => {
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const contentRef = React.useRef<HTMLDivElement>(null)
  const previousActiveElement = React.useRef<HTMLElement | null>(null)

  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    // Focus trap: handle Tab key to cycle within dialog
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !contentRef.current) return

      const focusableElements = getFocusableElements(contentRef.current)
      if (focusableElements.length === 0) return

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      // 如果当前焦点不在对话框内，将焦点移到第一个元素
      if (!contentRef.current.contains(document.activeElement)) {
        e.preventDefault()
        firstElement.focus()
        return
      }

      if (e.shiftKey) {
        // Shift + Tab: if on first element, go to last
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement.focus()
        }
      } else {
        // Tab: if on last element, go to first
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement.focus()
        }
      }
    }

    if (isOpen) {
      // Store currently focused element
      previousActiveElement.current = document.activeElement as HTMLElement
      
      document.addEventListener('keydown', handleEscape)
      document.addEventListener('keydown', handleTab)
      document.body.style.overflow = 'hidden'
      
      // Focus the first focusable element in the dialog
      setTimeout(() => {
        if (contentRef.current) {
          const focusableElements = getFocusableElements(contentRef.current)
          if (focusableElements.length > 0) {
            focusableElements[0].focus()
          } else {
            contentRef.current.focus()
          }
        }
      }, 0)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('keydown', handleTab)
      document.body.style.overflow = 'unset'
      
      // Restore focus to previously focused element
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        ref={overlayRef}
        className="fixed inset-0 bg-black/95 transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
        aria-label="关闭对话框"
      />
      
      {/* Content */}
      <div
        ref={contentRef}
        className={cn(
          "relative z-50 grid w-full max-w-lg scale-100 gap-4 bg-background p-6 shadow-2xl duration-200 animate-in fade-in-0 zoom-in-95 sm:rounded-lg md:w-full",
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "dialog-title" : undefined}
        tabIndex={-1}
      >
        <div className="flex flex-col space-y-1.5 text-center sm:text-left">
          {title && (
            <h2
              id="dialog-title"
              className="text-lg font-semibold leading-none tracking-tight text-foreground"
            >
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
