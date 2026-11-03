'use client'

import { Input as InputPrimitive } from '@base-ui/react/input'
import { cn } from '@/lib/utils'

export type InputProps = Omit<InputPrimitive.Props, 'className'> & { className?: string }

// Inside a Field it picks up the id, aria-invalid and aria-describedby on its own
export function Input({ className, ...props }: InputProps) {
  return <InputPrimitive data-slot="input" className={cn('input', className)} {...props} />
}
