'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ROUTES, useDashboard } from '@/components/dashboard/dashboard-context'
import { formatTime } from '@/lib/format'
import type { Metrics } from '@/lib/types'
import { MetricsCharts } from './metrics-charts'

// Nothing to measure yet: no projects (so no milestones either) and no ideas
function isEmpty(data: Metrics) {
  return data.project_progress.length === 0 && data.idea_totals.captured === 0
}

const SKELETON_BARS = [38, 64, 46, 84, 58, 72, 40, 90]

function MetricsSkeleton() {
  return <div className="metrics-grid" aria-busy="true" aria-label="Cargando métricas">
    {[0, 1, 2, 3].map((i) => <div key={i} className={i < 2 ? 'chart-card' : 'chart-card chart-wide'}>
      <Skeleton className="h-4 w-1/3" />
      <div className="skeleton-bars">{SKELETON_BARS.map((height, j) => <Skeleton key={j} style={{ height: `${height}%` }} />)}</div>
    </div>)}
  </div>
}

function EmptyMetrics() {
  return <div className="state-panel">
    <h3>Todavía no hay nada que medir</h3>
    <p>Las métricas aparecen cuando tienes proyectos, hitos e ideas.</p>
    <div className="metrics-links">
      <Link className="metrics-link" href={ROUTES.projects}>Crear un proyecto</Link>
      <Link className="metrics-link" href={ROUTES.projects}>Añadir hitos</Link>
      <Link className="metrics-link" href={ROUTES.ideas}>Anotar una idea</Link>
    </div>
  </div>
}

export function MetricsView() {
  const { metrics } = useDashboard()
  const { data, loading, refreshing, error, fetchedAt, ensure, refresh } = metrics

  useEffect(() => { ensure() }, [ensure])

  return <section className="projects-section">
    <div className="section-heading metrics-heading">
      <div><p className="eyebrow">Tu avance real</p><h2>Métricas</h2></div>
      <div className="metrics-refresh">
        {fetchedAt && <span>Actualizado a las <time dateTime={fetchedAt.toISOString()}>{formatTime(fetchedAt)}</time></span>}
        <Button variant="outline" className="metrics-refresh-btn" onClick={refresh} aria-busy={refreshing || undefined}>
          <RefreshCw className={refreshing ? 'spin' : undefined} data-icon="inline-start" aria-hidden="true" />
          {refreshing ? 'Actualizando…' : 'Actualizar'}
        </Button>
      </div>
    </div>
    {loading && <MetricsSkeleton />}
    {!loading && error && data === null && <div className="state-panel" role="alert">
      <h3>No pudimos cargar tus métricas</h3><p>{error}</p><Button variant="outline" className="metrics-refresh-btn" onClick={refresh}>Reintentar</Button>
    </div>}
    {error && data !== null && <div className="metrics-error" role="alert">
      <span>No se pudieron actualizar las métricas. {error}</span><Button variant="outline" className="metrics-refresh-btn" onClick={refresh}>Reintentar</Button>
    </div>}
    {data !== null && (isEmpty(data) ? <EmptyMetrics /> : <MetricsCharts data={data} />)}
  </section>
}
