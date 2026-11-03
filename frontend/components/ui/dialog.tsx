'use client'

import { useRef, type ReactNode } from 'react'
import { Dialog as DialogPrimitive } from '@base-ui/react/dialog'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { portalContainer } from '@/lib/portal-container'

export const Dialog = DialogPrimitive.Root

export interface DialogContentProps {
  // "modal" is centered; "side" is a right-hand panel. Both go full screen at 760px and below.
  variant?: 'modal' | 'side'
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  // Focus the first field of the body when opening; otherwise the panel itself gets focus
  focusFirstField?: boolean
  // Disables the close button while the caller blocks dismissal (e.g. a request in flight)
  closeDisabled?: boolean
}

const FIELDS = 'input:not([type="hidden"]), textarea, select'

// Focus trap, Escape, scroll lock, aria-labelledby (title) and focus return come from Base UI
export function DialogContent({ variant = 'modal', eyebrow, title, description, children, focusFirstField, closeDisabled }: DialogContentProps) {
  const popup = useRef<HTMLDivElement | null>(null)
  const body = useRef<HTMLDivElement | null>(null)
  const initialFocus = () => (focusFirstField ? body.current?.querySelector<HTMLElement>(FIELDS) : null) ?? popup.current

  return <DialogPrimitive.Portal container={portalContainer()}>
    <DialogPrimitive.Backdrop className="dialog-backdrop" />
    <DialogPrimitive.Viewport className="dialog-viewport" data-variant={variant}>
      <DialogPrimitive.Popup ref={popup} className="dialog-popup" data-variant={variant} aria-modal="true" initialFocus={initialFocus}>
        <div className="dialog-head">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <DialogPrimitive.Title className="dialog-title">{title}</DialogPrimitive.Title>
            {description && <DialogPrimitive.Description className="dialog-description">{description}</DialogPrimitive.Description>}
          </div>
          <DialogPrimitive.Close render={<Button variant="ghost" size="icon" aria-label="Cerrar" />} disabled={closeDisabled}>
            <X />
          </DialogPrimitive.Close>
        </div>
        <div ref={body} className="dialog-body">{children}</div>
      </DialogPrimitive.Popup>
    </DialogPrimitive.Viewport>
  </DialogPrimitive.Portal>
}
