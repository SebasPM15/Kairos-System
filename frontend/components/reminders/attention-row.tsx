'use client'

import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/projects/status-badge'
import { preloadDialog } from '@/components/dashboard/lazy-dialogs'
import { formatCount } from '@/lib/labels'
import type { ReminderAlert } from '@/lib/types'

// Same default as the bot's "Posponer" button
export const SNOOZE_DAYS = 7

export type RowAction = 'snooze' | 'mute'

export interface AttentionRowProps {
  alert: ReminderAlert
  // The action in flight for this project, if any
  busy: RowAction | null
  onOpen: () => void
  onSnooze: () => void
  onMute: () => void
}

function reason(alert: ReminderAlert): string {
  if (alert.kind === 'ready_to_finish') return 'Todos los hitos están hechos'
  const text = `${formatCount('day', alert.days_idle)} sin avance`
  return alert.milestones_total === 0 ? `${text} · Aún no tiene hitos` : text
}

export function AttentionRow({ alert, busy, onOpen, onSnooze, onMute }: AttentionRowProps) {
  const snoozeLabel = `Posponer ${formatCount('day', SNOOZE_DAYS)}`
  return <li className="attention-row">
    <div className="attention-main">
      <div className="attention-title">
        <h3 className="attention-name">{alert.name}</h3>
        <StatusBadge status={alert.status} />
      </div>
      <p className="attention-reason" data-kind={alert.kind}>{reason(alert)}</p>
      {alert.next_action && <p className="attention-next">Próxima acción: {alert.next_action}</p>}
    </div>
    <div className="attention-actions">
      <Button variant="outline" className="touch-target" onClick={onOpen} onPointerEnter={() => preloadDialog('drawer')} onFocus={() => preloadDialog('drawer')} aria-label={`Abrir ${alert.name}`}>Abrir</Button>
      <Button variant="outline" className="touch-target" onClick={onSnooze} disabled={busy !== null} loading={busy === 'snooze'} loadingText="Posponiendo…" aria-label={`${snoozeLabel}: ${alert.name}`}>{snoozeLabel}</Button>
      <Button variant="outline" className="touch-target" onClick={onMute} disabled={busy !== null} loading={busy === 'mute'} loadingText="Silenciando…" aria-label={`Silenciar: ${alert.name}`}>Silenciar</Button>
    </div>
  </li>
}
