import type { ComponentProps } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export type SelectProps = ComponentProps<'select'> & { wrapperClassName?: string }

// Native select (keyboard, mobile pickers and iOS zoom rules stay intact) with our own chevron
export function Select({ className, wrapperClassName, children, ...props }: SelectProps) {
  return <span className={cn('select', wrapperClassName)}>
    <select data-slot="select" className={className} {...props}>{children}</select>
    <ChevronDown aria-hidden="true" />
  </span>
}
