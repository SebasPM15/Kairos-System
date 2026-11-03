'use client'

import type { ReactElement, ReactNode } from 'react'
import { Tooltip as TooltipPrimitive } from '@base-ui/react/tooltip'

export interface TooltipProps {
  label: string
  // Off when the label is already visible (e.g. an expanded sidebar)
  disabled?: boolean
  // The element that triggers it, e.g. <Link />; it receives the children
  render: ReactElement
  children: ReactNode
}

// Opens on hover and on keyboard focus; the label is also the trigger's own text or aria-label
export function Tooltip({ label, disabled, render, children }: TooltipProps) {
  return <TooltipPrimitive.Root disabled={disabled}>
    <TooltipPrimitive.Trigger render={render}>{children}</TooltipPrimitive.Trigger>
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Positioner side="right" sideOffset={10}>
        <TooltipPrimitive.Popup className="tooltip">{label}</TooltipPrimitive.Popup>
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  </TooltipPrimitive.Root>
}
