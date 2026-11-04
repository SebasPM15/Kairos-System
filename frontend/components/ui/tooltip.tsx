'use client'

import { cloneElement, useEffect, useLayoutEffect, useRef, useState, type ComponentType, type ReactElement, type ReactNode } from 'react'
import type { TooltipPopupProps } from './tooltip-popup'

export interface TooltipProps {
  label: string
  // Off when the label is already visible (e.g. an expanded sidebar)
  disabled?: boolean
  // The element that triggers it, e.g. <Link />; it receives the children
  render: ReactElement
  children: ReactNode
}

let loaded: ComponentType<TooltipPopupProps> | null = null
let loading: Promise<ComponentType<TooltipPopupProps>> | null = null

function loadPopup() {
  loading ??= import('./tooltip-popup').then((m) => (loaded = m.TooltipPopup))
  return loading
}

// Opens on hover and on keyboard focus; the label is also the trigger's own text or aria-label.
// The Base UI tooltip (about 25 kB gzip with its positioning library) only downloads when a tooltip
// can actually show, i.e. with the sidebar collapsed. Until it arrives the bare trigger is rendered, and
// if the trigger has keyboard focus at the swap (the collapse button itself) focus is put back on it.
export function Tooltip({ label, disabled, render, children }: TooltipProps) {
  const [Popup, setPopup] = useState<ComponentType<TooltipPopupProps> | null>(() => loaded)
  const [trigger, setTrigger] = useState<HTMLElement | null>(null)
  const restoreFocus = useRef(false)

  useEffect(() => {
    if (disabled || Popup) return
    let live = true
    loadPopup().then((component) => {
      if (!live) return
      restoreFocus.current = document.activeElement === trigger
      setPopup(() => component)
    })
    return () => { live = false }
  }, [disabled, Popup, trigger])

  useLayoutEffect(() => {
    // `trigger` still points at the removed element in the commit that swaps; wait for the new one
    if (Popup && restoreFocus.current && trigger?.isConnected) {
      restoreFocus.current = false
      trigger.focus()
    }
  }, [Popup, trigger])

  if (!Popup) return cloneElement(render as ReactElement<{ ref?: unknown }>, { ref: setTrigger }, children)
  return <Popup label={label} disabled={disabled} render={render} triggerRef={setTrigger}>{children}</Popup>
}
