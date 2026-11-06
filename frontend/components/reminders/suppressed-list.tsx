'use client'

import { ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatShortDate } from '@/lib/format'
import type { ReminderSuppressed } from '@/lib/types'

export interface SuppressedListProps {
  items: ReminderSuppressed[]
  // The project being reactivated, if any
  busyId: number | null
  onReactivate: (item: ReminderSuppressed) => void
}

function stateText(item: ReminderSuppressed): string {
  if (item.muted) return 'Silenciado'
  return item.snoozed_until ? `Pospuesto hasta el ${formatShortDate(item.snoozed_until)}` : ''
}

// Collapsed by default: these are the projects the user chose not to hear about, kept reachable so
// that nothing stays silenced without a way back.
export function SuppressedList({ items, busyId, onReactivate }: SuppressedListProps) {
  if (items.length === 0) return null
  return <details className="attention-suppressed">
    <summary><ChevronRight aria-hidden="true" />Pospuestos y silenciados ({items.length})</summary>
    <ul className="attention-list">
      {items.map((item) => <li key={item.project_id} className="attention-row">
        <div className="attention-main">
          <h3 className="attention-name">{item.name}</h3>
          <p className="attention-reason">{stateText(item)}</p>
        </div>
        <div className="attention-actions">
          <Button variant="outline" className="touch-target" onClick={() => onReactivate(item)} disabled={busyId !== null} loading={busyId === item.project_id} loadingText="Reactivando…" aria-label={`Reactivar: ${item.name}`}>Reactivar</Button>
        </div>
      </li>)}
    </ul>
  </details>
}
