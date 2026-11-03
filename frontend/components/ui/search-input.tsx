'use client'

import { useRef } from 'react'
import { Input as InputPrimitive } from '@base-ui/react/input'
import { Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SearchInputProps {
  value: string
  onValueChange: (value: string) => void
  // Accessible name; the placeholder alone is not a label
  label: string
  placeholder?: string
  className?: string
}

// Search box with a clear button (only while there is text); Escape clears too
export function SearchInput({ value, onValueChange, label, placeholder, className }: SearchInputProps) {
  const input = useRef<HTMLInputElement | null>(null)
  const clear = () => { onValueChange(''); input.current?.focus() }

  return <div role="search" className={cn('search', className)}>
    <Search aria-hidden="true" />
    <InputPrimitive
      ref={input}
      value={value}
      onValueChange={onValueChange}
      onKeyDown={(event) => { if (event.key === 'Escape' && value) { event.preventDefault(); clear() } }}
      aria-label={label}
      placeholder={placeholder}
      autoComplete="off"
    />
    {value && <button type="button" className="search-clear" onClick={clear} aria-label="Limpiar búsqueda"><X aria-hidden="true" /></button>}
  </div>
}
