'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from '@/components/ui/toaster'
import { useDashboard } from '@/components/dashboard/dashboard-context'
import { TOAST, formatCount } from '@/lib/labels'
import type { ReminderPrefsUpdate } from '@/lib/types'
import * as api from '@/lib/api'
import { AttentionRow, SNOOZE_DAYS, type RowAction } from './attention-row'
import { SuppressedList } from './suppressed-list'

function AttentionSkeleton() {
  return <div className="attention-list" aria-busy="true" aria-label="Cargando alertas">
    {[0, 1].map((i) => <div key={i} className="attention-row"><Skeleton className="h-[58px] w-full rounded-[8px]" /></div>)}
  </div>
}

// Projects that went quiet or are ready to be finished. Live from GET /reminders: nothing is "read" or
// dismissed here, an alert goes away when the project moves, or when it is snoozed or muted.
export function AttentionBlock() {
  const { reminders, setSelectedId, showError } = useDashboard()
  const { data, loading, refreshing, error, watch, refresh } = reminders
  // One mutation at a time: [project id, what it is doing]
  const [busy, setBusy] = useState<[number, RowAction | 'reactivate'] | null>(null)

  useEffect(() => watch(), [watch])

  const run = async (projectId: number, action: RowAction | 'reactivate', body: ReminderPrefsUpdate, title: string, name: string) => {
    setBusy([projectId, action])
    try {
      await api.reminders.update(projectId, body)
      toast.success(title, name)
    } catch (failure) {
      // The button stays where it was, so retrying is one click away
      showError(failure)
    } finally {
      setBusy(null)
    }
  }

  const alerts = data?.alerts ?? []
  const suppressed = data?.suppressed ?? []
  return <section className="attention" aria-labelledby="attention-title">
    <div className="section-heading">
      <h2 id="attention-title">Necesitan atención</h2>
      {data && <span className="section-count">{formatCount('alert', alerts.length)}</span>}
    </div>
    {loading && <AttentionSkeleton />}
    {error && <div className="attention-error" role="alert">
      <p>{data ? 'No pudimos actualizar las alertas.' : 'No pudimos cargar las alertas.'} {error}</p>
      <Button variant="outline" className="touch-target" onClick={refresh} loading={refreshing} loadingText="Reintentando…">Reintentar</Button>
    </div>}
    {data && alerts.length === 0 && <p className="attention-empty">Sin alertas: tus proyectos tienen actividad reciente.</p>}
    {alerts.length > 0 && <ul className="attention-list">
      {alerts.map((alert) => <AttentionRow
        key={alert.project_id}
        alert={alert}
        busy={busy && busy[0] === alert.project_id && busy[1] !== 'reactivate' ? busy[1] : null}
        onOpen={() => setSelectedId(alert.project_id)}
        onSnooze={() => run(alert.project_id, 'snooze', { snooze_days: SNOOZE_DAYS }, TOAST.remindersSnoozed, alert.name)}
        onMute={() => run(alert.project_id, 'mute', { muted: true }, TOAST.remindersMuted, alert.name)}
      />)}
    </ul>}
    <SuppressedList
      items={suppressed}
      busyId={busy && busy[1] === 'reactivate' ? busy[0] : null}
      onReactivate={(item) => run(item.project_id, 'reactivate', { snooze_days: null, muted: false }, TOAST.remindersReactivated, item.name)}
    />
  </section>
}
