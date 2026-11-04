import Link from 'next/link'
import { ROUTES } from '@/components/dashboard/dashboard-context'
import { StatusBadge } from '@/components/projects/status-badge'
import { pluralLabel } from '@/lib/labels'
import type { Metrics } from '@/lib/types'
import { ChartCard, ChartEmpty } from './chart-card'

export function ProgressList({ data }: { data: Metrics }) {
  const projects = data.project_progress
  return <ChartCard
    id="progress"
    title="Avance por proyecto"
    subtitle="Hitos completados sobre el total; los activos primero"
    empty={projects.length === 0 ? <ChartEmpty>
      <p>Aún no tienes proyectos.</p>
      <Link className="metrics-link" href={ROUTES.projects}>Crear un proyecto</Link>
    </ChartEmpty> : undefined}
  >
    <ul className="progress-list">
      {projects.map((project) => <li key={project.id} className="progress-item">
        <div className="progress-item-head">
          <span className="progress-name" title={project.name}>{project.name}</span>
          <StatusBadge status={project.status} />
        </div>
        <div className="progress-track" role="presentation"><div className="progress-value" style={{ width: `${project.progress}%` }} /></div>
        <span className="progress-meta">{project.milestones_total === 0
          ? 'sin hitos'
          : `${project.milestones_done}/${project.milestones_total} ${pluralLabel('milestone', project.milestones_total)} · ${project.progress} %`}</span>
      </li>)}
    </ul>
  </ChartCard>
}
