import { AlertTriangle, ArrowUpRight, CirclePlus } from 'lucide-react'
import type { Project } from '@/lib/types'
import { NO_NEXT_ACTION_LABEL } from '@/lib/labels'
import { isAbandoned } from '@/lib/project-health'
import { StatusBadge } from './status-badge'

function ProgressBar({ progress }: { progress: number }) { return <div className="progress-wrap"><div className="progress-track"><div className="progress-value" style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div> }
function daysTone(days: number) { return days < 7 ? 'fresh' : days <= 14 ? 'warm' : 'stale' }

export interface ProjectCardProps {
  project: Project
  onOpen: () => void
}

export function ProjectCard({ project, onOpen }: ProjectCardProps) {
  const days = project.days_since_activity
  const abandoned = isAbandoned(project)
  return <button className="project-card" onClick={onOpen} aria-label={`Abrir ${project.name}`}>
    <div className="card-top"><div><h3>{project.name}</h3><p>{project.description}</p></div><StatusBadge status={project.status} /></div>
    <div className="progress-label"><span>Progreso</span><span>{project.milestones_done}/{project.milestones_total} hitos</span></div><ProgressBar progress={project.progress} />
    <div className={`touched ${daysTone(days)}`}>{abandoned ? <AlertTriangle data-icon="inline-start" /> : null}<span>{days} días sin tocar</span>{abandoned ? <em>Proyecto abandonado</em> : null}</div>
    <div className={`next-action ${!project.next_action ? 'empty-action' : ''}`}><span>{project.next_action ?? NO_NEXT_ACTION_LABEL}</span>{!project.next_action ? <CirclePlus data-icon="inline-end" /> : <ArrowUpRight data-icon="inline-end" />}</div>
  </button>
}
