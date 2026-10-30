import { AlertTriangle, ArrowUpRight, CirclePlus } from 'lucide-react'
import type { Project } from '@/lib/types'
import { StatusBadge } from './status-badge'

function ProgressBar({ progress }: { progress: number }) { return <div className="progress-wrap"><div className="progress-track"><div className="progress-value" style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div> }
function daysTone(days: number) { return days < 7 ? 'fresh' : days <= 14 ? 'warm' : 'stale' }

export interface ProjectCardProps {
  project: Project
  onOpen: () => void
}

export function ProjectCard({ project, onOpen }: ProjectCardProps) {
  const days = project.days_since_activity
  return <button className="project-card" onClick={onOpen} aria-label={`Abrir ${project.name}`}>
    <div className="card-top"><div><h3>{project.name}</h3><p>{project.description}</p></div><StatusBadge status={project.status} /></div>
    <div className="progress-label"><span>Progreso</span><span>{project.milestones_done}/{project.milestones_total} hitos</span></div><ProgressBar progress={project.progress} />
    <div className={`touched ${daysTone(days)}`}>{days > 30 && project.status === 'active' ? <AlertTriangle data-icon="inline-start" /> : null}<span>{days} días sin tocar</span>{days > 30 && project.status === 'active' ? <em>Proyecto abandonado</em> : null}</div>
    <div className={`next-action ${!project.next_action ? 'empty-action' : ''}`}><span>{project.next_action ?? 'Sin próxima acción definida'}</span>{!project.next_action ? <CirclePlus data-icon="inline-end" /> : <ArrowUpRight data-icon="inline-end" />}</div>
  </button>
}
