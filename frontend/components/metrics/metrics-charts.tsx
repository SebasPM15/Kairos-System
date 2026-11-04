import Link from 'next/link'
import { ROUTES } from '@/components/dashboard/dashboard-context'
import { formatCount } from '@/lib/labels'
import { formatWeekStart } from '@/lib/format'
import type { Metrics, WeekCount } from '@/lib/types'
import { ChartCard, ChartEmpty } from './chart-card'
import { ProgressList } from './progress-list'
import { StatusBars } from './status-bars'
import { NARROW_WEEKS, WeekChart, WeekTable, type WeekSeries } from './week-chart'

const total = (points: WeekCount[]) => points.reduce((sum, point) => sum + point.count, 0)

function peak(points: WeekCount[]): string {
  const best = points.reduce((a, b) => (b.count > a.count ? b : a))
  return `el máximo fue ${best.count} en la semana del ${formatWeekStart(best.week_start)}`
}

function WeeksSubtitle({ data }: { data: Metrics }) {
  return <>
    <span className="only-wide">Últimas {formatCount('week', data.weeks)}</span>
    <span className="only-narrow">Últimas {formatCount('week', Math.min(NARROW_WEEKS, data.weeks))}</span>
    {' '}de lunes a domingo ({data.timezone}). La última está en curso.
  </>
}

function MilestonesChart({ data }: { data: Metrics }) {
  const points = data.milestones_completed
  const series: WeekSeries[] = [{ name: 'Hitos completados', points, style: 'solid' }]
  const done = total(points)
  const summary = `Hitos completados por semana. ${formatCount('milestoneCompleted', done)} en las últimas ${formatCount('week', data.weeks)}; ${peak(points)}. La última semana está en curso.`
  return <ChartCard
    id="milestones"
    wide
    title="Hitos completados por semana"
    subtitle={<WeeksSubtitle data={data} />}
    note="Si reabres un hito, deja de contar en su semana."
    empty={done === 0 ? <ChartEmpty>
      <p>Aún no completas hitos en estas {formatCount('week', data.weeks)}.</p>
      <Link className="metrics-link" href={ROUTES.projects}>Ir a los proyectos</Link>
    </ChartEmpty> : undefined}
    table={<WeekTable series={series} currentWeek={data.current_week_start} caption="Hitos completados por semana" />}
  >
    <WeekChart series={series} currentWeek={data.current_week_start} summary={summary} />
  </ChartCard>
}

function IdeasChart({ data }: { data: Metrics }) {
  const series: WeekSeries[] = [
    { name: 'Capturadas', points: data.ideas_captured, style: 'solid' },
    { name: 'Asignadas a un proyecto', points: data.ideas_assigned, style: 'hatched' },
  ]
  const captured = total(data.ideas_captured)
  const assigned = total(data.ideas_assigned)
  const { idea_totals: totals } = data
  const summary = `Ideas por semana. ${formatCount('ideaCaptured', captured)} y ${formatCount('ideaAssigned', assigned)} en las últimas ${formatCount('week', data.weeks)}. La última semana está en curso.`
  return <ChartCard
    id="ideas"
    wide
    title="Ideas asignadas a un proyecto"
    subtitle={<><WeeksSubtitle data={data} /> En total: {formatCount('ideaCaptured', totals.captured)}, {totals.in_inbox} en la bandeja y {totals.assigned} en proyectos.</>}
    note="Las ideas asignadas antes de este registro se cuentan en su semana de captura."
    empty={captured === 0 && assigned === 0 ? <ChartEmpty>
      <p>No capturaste ni asignaste ideas en estas {formatCount('week', data.weeks)}.</p>
      <Link className="metrics-link" href={ROUTES.ideas}>Anotar una idea</Link>
    </ChartEmpty> : undefined}
    table={<WeekTable series={series} currentWeek={data.current_week_start} caption="Ideas capturadas y asignadas por semana" />}
  >
    <WeekChart series={series} currentWeek={data.current_week_start} summary={summary} />
  </ChartCard>
}

export function MetricsCharts({ data }: { data: Metrics }) {
  return <div className="metrics-grid">
    <StatusBars data={data} />
    <ProgressList data={data} />
    <MilestonesChart data={data} />
    <IdeasChart data={data} />
  </div>
}
