'use client'

import { useLayoutEffect, useRef } from 'react'
import { Input as InputPrimitive } from '@base-ui/react/input'
import { cn } from '@/lib/utils'

export type TextareaProps = Omit<InputPrimitive.Props, 'className' | 'type'> & {
  className?: string
  // Enter sends the form and Shift+Enter inserts a line break
  submitOnEnter?: boolean
}

// Grows with its content up to the CSS max-height, then scrolls inside
export function Textarea({ className, value, submitOnEnter, onKeyDown, ref, ...props }: TextareaProps) {
  const own = useRef<HTMLInputElement | null>(null)

  useLayoutEffect(() => {
    const element = own.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${element.scrollHeight + 2}px`
  }, [value])

  return <InputPrimitive
    ref={(element: HTMLInputElement | null) => {
      own.current = element
      if (typeof ref === 'function') ref(element)
      else if (ref) ref.current = element
    }}
    data-slot="textarea"
    className={cn('input textarea', className)}
    render={<textarea rows={1} />}
    value={value}
    onKeyDown={(event) => {
      onKeyDown?.(event)
      if (!submitOnEnter || event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }}
    {...props}
  />
}
