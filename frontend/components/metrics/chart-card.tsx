import type { ReactNode } from 'react'

export interface ChartCardProps {
  title: string
  // Id prefix for the heading, so the card is a labelled region
  id: string
  subtitle?: ReactNode
  wide?: boolean
  // Shown instead of `children` and `table` when the chart has nothing to plot
  empty?: ReactNode
  note?: string
  // The chart itself, with role="img" and an aria-label
  children?: ReactNode
  // Full data, inside <details>, for people who cannot see the bars
  table?: ReactNode
}

export function ChartCard({ title, id, subtitle, wide, empty, note, children, table }: ChartCardProps) {
  return <section className={wide ? 'chart-card chart-wide' : 'chart-card'} aria-labelledby={`${id}-title`}>
    <div className="chart-head">
      <h3 id={`${id}-title`}>{title}</h3>
      {subtitle && <p className="chart-sub">{subtitle}</p>}
    </div>
    {empty ?? <>
      {children}
      {table && <details className="chart-data"><summary>Ver los datos en una tabla</summary>{table}</details>}
    </>}
    {note && <p className="chart-note">{note}</p>}
  </section>
}

export function ChartEmpty({ children }: { children: ReactNode }) {
  return <div className="chart-empty">{children}</div>
}
