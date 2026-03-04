import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

let dialogIdSequence = 0
const openDialogStack: number[] = []

let bodyScrollLockCount = 0
let previousBodyOverflow: string | null = null

const lockBodyScroll = () => {
  if (typeof document === 'undefined') return

  if (bodyScrollLockCount === 0) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  bodyScrollLockCount += 1
}

const unlockBodyScroll = () => {
  if (typeof document === 'undefined') return

  bodyScrollLockCount = Math.max(0, bodyScrollLockCount - 1)
  if (bodyScrollLockCount === 0) {
    document.body.style.overflow = previousBodyOverflow ?? ''
    previousBodyOverflow = null
  }
}

const pushDialog = (id: number) => {
  openDialogStack.push(id)
}

const popDialog = (id: number) => {
  const index = openDialogStack.lastIndexOf(id)
  if (index !== -1) openDialogStack.splice(index, 1)
}

const isTopDialog = (id: number) => openDialogStack[openDialogStack.length - 1] === id

export interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children?: React.ReactNode
  className?: string
  /** 自定义外层容器的 className，可用于调整嵌套场景下的 z-index */
  containerClassName?: string
  /** 禁用关闭行为（遮罩点击 / Esc / 右上角关闭按钮） */
  disableClose?: boolean
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

const Dialog: React.FC<DialogProps> = ({ isOpen, onClose, title, children, className, containerClassName, disableClose = false }) => {
  const dialogId = React.useRef<number>(++dialogIdSequence).current
  const titleId = React.useId()
  const onCloseRef = React.useRef(onClose)
  const disableCloseRef = React.useRef(disableClose)
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const contentRef = React.useRef<HTMLDivElement>(null)
  const previousActiveElement = React.useRef<HTMLElement | null>(null)

  React.useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  React.useEffect(() => {
    disableCloseRef.current = disableClose
  }, [disableClose])

  React.useEffect(() => {
    if (!isOpen) return

    pushDialog(dialogId)
    lockBodyScroll()

    const handleEscape = (e: KeyboardEvent) => {
      if (!isTopDialog(dialogId)) return
      if (disableCloseRef.current) return
      if (e.key === 'Escape') onCloseRef.current()
    }

    // Focus trap: handle Tab key to cycle within dialog
    const handleTab = (e: KeyboardEvent) => {
      if (!isTopDialog(dialogId)) return
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

    // Store currently focused element
    previousActiveElement.current = document.activeElement as HTMLElement
    
    document.addEventListener('keydown', handleEscape)
    document.addEventListener('keydown', handleTab)
    
    // Focus the first meaningful focusable element in the dialog (avoid focusing the close button first)
    setTimeout(() => {
      if (!contentRef.current || !isTopDialog(dialogId)) return

      // 如果子组件已经把焦点放进弹窗（例如 ConfirmDialog 自动聚焦确认按钮），不要覆盖它
      if (contentRef.current.contains(document.activeElement)) return

      const focusableElements = getFocusableElements(contentRef.current)
      const firstNonClose = focusableElements.find(el => !el.hasAttribute('data-dialog-close'))
      const target = firstNonClose ?? focusableElements[0]

      if (target) {
        target.focus()
      } else {
        contentRef.current.focus()
      }
    }, 0)

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('keydown', handleTab)
      popDialog(dialogId)
      unlockBodyScroll()
      
      // Restore focus to previously focused element
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen, dialogId])

  if (!isOpen) return null

  // 根据 containerClassName 判断是否使用自定义层级（用于嵌套场景）
  const isNested = !!containerClassName
  const outerZIndex = isNested ? 'z-[210]' : 'z-[200]'
  const backdropZIndex = isNested ? 'z-[209]' : 'z-[199]'
  const contentZIndex = isNested ? 'z-[210]' : 'z-[200]'

  return (
    <div className={cn("fixed inset-0 flex items-center justify-center overflow-y-auto", outerZIndex, containerClassName)}>
      {/* Backdrop - 独立的遮罩层 */}
      <div
        ref={overlayRef}
        className={cn("fixed inset-0 bg-black/60 backdrop-blur-none md:backdrop-blur-sm transition-opacity animate-in fade-in duration-200", backdropZIndex)}
        onClick={(e) => {
          if (disableClose) return
          if (e.target === e.currentTarget) {
            onClose();
          }
        }}
        aria-label="关闭对话框"
        aria-disabled={disableClose}
      />
      
      {/* Content - 确保在遮罩层之上 */}
      <div
        ref={contentRef}
        className={cn(
          "relative grid w-full max-w-lg scale-100 gap-4 bg-background p-6 shadow-2xl duration-200 animate-in fade-in-0 zoom-in-95 sm:rounded-lg md:w-full mx-4",
          contentZIndex,
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
      >
        <div className="flex flex-col space-y-1.5 text-center sm:text-left">
          {title && (
            <h2
              id={titleId}
              className="text-lg font-semibold leading-none tracking-tight text-foreground"
            >
              {title}
            </h2>
          )}
          <button
            onClick={onClose}
            disabled={disableClose}
            data-dialog-close
            className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-all duration-150 hover:opacity-100 active:scale-[var(--scale-click-icon)] active:opacity-60 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-40 data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">关闭</span>
          </button>
        </div>
        
        {children}
      </div>
    </div>
  )
}

export { Dialog }
