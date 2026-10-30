'use client'

import * as React from 'react'
import { AlertDialog as AlertDialogPrimitive } from '@base-ui/react/alert-dialog'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const AlertDialog = AlertDialogPrimitive.Root

// The portal renders into `container` (the dashboard) so the dashboard's own theme variables apply
function AlertDialogContent({
  className,
  container,
  ...props
}: AlertDialogPrimitive.Popup.Props & { container?: HTMLElement | null }) {
  return (
    <AlertDialogPrimitive.Portal container={container}>
      <AlertDialogPrimitive.Backdrop className="fixed inset-0 z-[40] bg-black/50 transition-opacity data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
      <AlertDialogPrimitive.Popup
        data-slot="alert-dialog-content"
        className={cn(
          'fixed top-1/2 left-1/2 z-[41] grid w-[min(420px,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2 gap-3 rounded-xl border border-[var(--line)] bg-[var(--card)] p-5 text-[var(--foreground)] shadow-xl transition-opacity data-[ending-style]:opacity-0 data-[starting-style]:opacity-0',
          className,
        )}
        {...props}
      />
    </AlertDialogPrimitive.Portal>
  )
}

function AlertDialogTitle({ className, ...props }: AlertDialogPrimitive.Title.Props) {
  return <AlertDialogPrimitive.Title className={cn('text-base font-semibold', className)} {...props} />
}

function AlertDialogDescription({ className, ...props }: AlertDialogPrimitive.Description.Props) {
  return <AlertDialogPrimitive.Description className={cn('text-sm leading-relaxed text-[var(--muted)]', className)} {...props} />
}

function AlertDialogFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('mt-2 flex justify-end gap-2', className)} {...props} />
}

function AlertDialogCancel({ className, ...props }: AlertDialogPrimitive.Close.Props) {
  return <AlertDialogPrimitive.Close className={className} render={<Button variant="outline" size="sm" />} {...props} />
}

export { AlertDialog, AlertDialogContent, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel }
