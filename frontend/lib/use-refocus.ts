import { useEffect, useRef, type RefObject } from 'react'

// Disabling a control while it submits drops its focus; give it back when the submit ends
export function useRefocus(busy: boolean, target: RefObject<HTMLElement | null>) {
  const wasBusy = useRef(false)
  useEffect(() => {
    if (wasBusy.current && !busy) target.current?.focus()
    wasBusy.current = busy
  }, [busy, target])
}
