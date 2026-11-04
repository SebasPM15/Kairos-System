'use client'

import type { ReactElement, ReactNode } from 'react'
import { Tooltip as TooltipPrimitive } from '@base-ui/react/tooltip'

export interface TooltipPopupProps {
  label: string
  disabled?: boolean
  render: ReactElement
  triggerRef: (element: HTMLButtonElement | null) => void
  children: ReactNode
}

// The Base UI tooltip itself; ui/tooltip.tsx loads it on demand so the library stays out of the first load
export function TooltipPopup({ label, disabled, render, triggerRef, children }: TooltipPopupProps) {
  return <TooltipPrimitive.Root disabled={disabled}>
    <TooltipPrimitive.Trigger ref={triggerRef} render={render}>{children}</TooltipPrimitive.Trigger>
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Positioner side="right" sideOffset={10}>
        <TooltipPrimitive.Popup className="tooltip">{label}</TooltipPrimitive.Popup>
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  </TooltipPrimitive.Root>
}
