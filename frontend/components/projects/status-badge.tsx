import type { ProjectStatus } from '@/lib/types'
import { statusLabel } from '@/lib/labels'

const statusTone: Record<ProjectStatus, string> = { active: 'status-active', paused: 'status-paused', idea: 'status-idea', done: 'status-done' }

export interface StatusBadgeProps {
  status: ProjectStatus
}

export function StatusBadge({ status }: StatusBadgeProps) { return <span className={`status-badge ${statusTone[status]}`}>{statusLabel[status]}</span> }
