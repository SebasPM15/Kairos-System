'use client'

import { Checkbox as CheckboxPrimitive } from '@base-ui/react/checkbox'
import { Check } from 'lucide-react'

export type CheckboxProps = Omit<CheckboxPrimitive.Root.Props, 'className' | 'children'>

// Square box with the lime check; keyboard focus uses the global ring on role="checkbox"
export function Checkbox(props: CheckboxProps) {
  return <CheckboxPrimitive.Root data-slot="checkbox" className="checkmark" {...props}>
    <CheckboxPrimitive.Indicator><Check aria-hidden="true" /></CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
}
