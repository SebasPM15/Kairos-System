'use client'

import type { ReactNode } from 'react'
import { Field as FieldPrimitive } from '@base-ui/react/field'
import { cn } from '@/lib/utils'

export interface FieldProps {
  label: string
  // Keeps the label for assistive tech when the layout leaves no room for it; never use a placeholder instead
  hideLabel?: boolean
  description?: string
  // Message to show; a non-empty value marks the control as invalid and links it with aria-describedby
  error?: string | null
  className?: string
  children: ReactNode
}

// Label + control + help + error. The control (Input, Textarea) must be a descendant.
export function Field({ label, hideLabel, description, error, className, children }: FieldProps) {
  return <FieldPrimitive.Root invalid={!!error} className={cn('field', className)}>
    <FieldPrimitive.Label className={hideLabel ? 'sr-only' : 'field-label'}>{label}</FieldPrimitive.Label>
    {children}
    {description && <FieldPrimitive.Description className="field-help">{description}</FieldPrimitive.Description>}
    <FieldPrimitive.Error match={!!error} className="field-error" role="alert">{error}</FieldPrimitive.Error>
  </FieldPrimitive.Root>
}
