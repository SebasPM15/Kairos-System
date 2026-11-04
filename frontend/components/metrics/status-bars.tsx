import Link from 'next/link'
import { ROUTES } from '@/components/dashboard/dashboard-context'
import { formatCount, statusLabel } from '@/lib/labels'
import type { Metrics } from '@/lib/types'
import { ChartCard, ChartEmpty } from './chart-card'

export function StatusBars({ data }: { data: Metrics }) {
  const rows = data.projects_by_status
  const total = rows.reduce((sum, row) => sum + row.count, 0)
  const max = Math.max(1, ...rows.map((row) => row.count))
  const summary = `Proyectos por estado. ${rows.map((row) => `${statusLabel[row.status]}: ${row.count}`).join('. ')}.`

  return <ChartCard
    id="status"
    title="Proyectos por estado"
    subtitle={formatCount('project', total)}
    empty={total === 0 ? <ChartEmpty>
      <p>Aún no tienes proyectos.</p>
      <Link className="metrics-link" href={ROUTES.projects}>Crear un proyecto</Link>
    </ChartEmpty> : undefined}
  >
    <div role="img" aria-label={summary} className="status-bars">
      {rows.map((row) => <div key={row.status} className="status-row">
        <span className="status-name">{statusLabel[row.status]}</span>
        <span className="status-track"><span className="bar bar-h" data-zero={row.count === 0 || undefined} style={{ width: `${(row.count / max) * 100}%` }} /></span>
        <span className="bar-value">{row.count}</span>
      </div>)}
    </div>
  </ChartCard>
}
