'use client'

import type { ReactNode } from 'react'
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
  initialFocus?: DialogPrimitive.Popup.Props['initialFocus']
  finalFocus?: DialogPrimitive.Popup.Props['finalFocus']
}

// Focus trap, Escape, scroll lock, aria-labelledby (title) and focus return come from Base UI
export function DialogContent({ variant = 'modal', eyebrow, title, description, children, initialFocus, finalFocus }: DialogContentProps) {
  return <DialogPrimitive.Portal container={portalContainer()}>
    <DialogPrimitive.Backdrop className="dialog-backdrop" />
    <DialogPrimitive.Viewport className="dialog-viewport" data-variant={variant}>
      <DialogPrimitive.Popup
        className="dialog-popup"
        data-variant={variant}
        initialFocus={initialFocus}
        finalFocus={finalFocus}
      >
        <div className="dialog-head">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <DialogPrimitive.Title className="dialog-title">{title}</DialogPrimitive.Title>
            {description && <DialogPrimitive.Description className="dialog-description">{description}</DialogPrimitive.Description>}
          </div>
          <DialogPrimitive.Close render={<Button variant="ghost" size="icon" aria-label="Cerrar" />}>
            <X />
          </DialogPrimitive.Close>
        </div>
        <div className="dialog-body">{children}</div>
      </DialogPrimitive.Popup>
    </DialogPrimitive.Viewport>
  </DialogPrimitive.Portal>
}
