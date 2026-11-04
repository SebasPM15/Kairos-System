import type { CSSProperties } from 'react'
import { formatWeekStart } from '@/lib/format'
import type { WeekCount } from '@/lib/types'

export interface WeekSeries {
  name: string
  points: WeekCount[]
  // Solid fill, or hatched with an outline: the pattern tells two series apart without color
  style: 'solid' | 'hatched'
}

// At 760px and below only the latest weeks are drawn (the table keeps all of them)
export const NARROW_WEEKS = 8

export interface WeekChartProps {
  series: WeekSeries[]
  currentWeek: string
  summary: string
}

// Plain HTML and CSS bars. Values are text, always visible; the bars are not interactive.
export function WeekChart({ series, currentWeek, summary }: WeekChartProps) {
  const weeks = series[0].points.map((point) => point.week_start)
  const max = Math.max(1, ...series.flatMap((s) => s.points.map((point) => point.count)))
  return <>
    <div role="img" aria-label={summary} className="week-chart">
      {weeks.map((week, index) => <div
        key={week}
        className="week-col"
        data-older={index < weeks.length - NARROW_WEEKS || undefined}
        data-alt={(weeks.length - 1 - index) % 2 === 1 || undefined}
      >
        <div className="week-bars">
          {series.map((s) => {
            const count = s.points[index].count
            return <div key={s.name} className="week-slot">
              <span className="bar-value">{count}</span>
              <span className="bar" data-style={s.style} data-zero={count === 0 || undefined} style={{ '--p': count / max } as CSSProperties} />
            </div>
          })}
        </div>
        <span className="week-label">{formatWeekStart(week)}</span>
        {week === currentWeek && <span className="week-partial">parcial</span>}
      </div>)}
    </div>
    {series.length > 1 && <ul className="chart-legend">
      {series.map((s) => <li key={s.name}><span className="swatch" data-style={s.style} aria-hidden="true" />{s.name}</li>)}
    </ul>}
  </>
}

export function WeekTable({ series, currentWeek, caption }: Omit<WeekChartProps, 'summary'> & { caption: string }) {
  return <table className="command-table data-table">
    <caption className="sr-only">{caption}</caption>
    <thead><tr><th scope="col">Semana</th>{series.map((s) => <th key={s.name} scope="col">{s.name}</th>)}</tr></thead>
    <tbody>{series[0].points.map((point, index) => <tr key={point.week_start}>
      <th scope="row">Semana del {formatWeekStart(point.week_start)}{point.week_start === currentWeek ? ' (en curso)' : ''}</th>
      {series.map((s) => <td key={s.name}>{s.points[index].count}</td>)}
    </tr>)}</tbody>
  </table>
}
