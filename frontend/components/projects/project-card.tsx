import { AlertTriangle, ArrowUpRight, CirclePlus } from 'lucide-react'
import type { Project, StaleAfterDays } from '@/lib/types'
import { NO_NEXT_ACTION_LABEL, formatCount, pluralLabel } from '@/lib/labels'
import { daysTone, isStale } from '@/lib/project-health'
import { preloadDialog } from '@/components/dashboard/lazy-dialogs'
import { StatusBadge } from './status-badge'

function ProgressBar({ progress }: { progress: number }) { return <div className="progress-wrap"><div className="progress-track"><div className="progress-value" style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div> }

export interface ProjectCardProps {
  project: Project
  onOpen: () => void
  // From GET /config; null until it answers, so nothing is flagged meanwhile
  staleAfterDays: StaleAfterDays | null
}

export function ProjectCard({ project, onOpen, staleAfterDays }: ProjectCardProps) {
  const days = project.days_since_activity
  const stalled = isStale(project, staleAfterDays)
  return <button className="project-card" onClick={onOpen} onPointerEnter={() => preloadDialog('drawer')} onFocus={() => preloadDialog('drawer')} aria-label={`Abrir ${project.name}`}>
    <div className="card-top"><div><h3>{project.name}</h3><p>{project.description}</p></div><StatusBadge status={project.status} /></div>
    <div className="progress-label"><span>Progreso</span><span>{project.milestones_done}/{project.milestones_total} {pluralLabel('milestone', project.milestones_total)}</span></div><ProgressBar progress={project.progress} />
    <div className={`touched ${daysTone(project, staleAfterDays)}`}>{stalled ? <AlertTriangle data-icon="inline-start" /> : null}<span>{formatCount('day', days)} sin tocar</span>{stalled ? <em>Sin avance</em> : null}</div>
    <div className={`next-action ${!project.next_action ? 'empty-action' : ''}`}><span>{project.next_action ?? NO_NEXT_ACTION_LABEL}</span>{!project.next_action ? <CirclePlus data-icon="inline-end" /> : <ArrowUpRight data-icon="inline-end" />}</div>
  </button>
}
