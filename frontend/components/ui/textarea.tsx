'use client'

import { useLayoutEffect, useRef } from 'react'
import { Input as InputPrimitive } from '@base-ui/react/input'
import { cn } from '@/lib/utils'

export type TextareaProps = Omit<InputPrimitive.Props, 'className' | 'type'> & { className?: string }

// Grows with its content up to the CSS max-height, then scrolls inside
export function Textarea({ className, value, ...props }: TextareaProps) {
  const ref = useRef<HTMLElement | null>(null)

  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${element.scrollHeight + 2}px`
  }, [value])

  return <InputPrimitive
    ref={ref}
    data-slot="textarea"
    className={cn('input textarea', className)}
    render={<textarea rows={1} />}
    value={value}
    {...props}
  />
}
