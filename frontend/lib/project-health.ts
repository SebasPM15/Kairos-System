import type { Project } from './types'

// Presentation threshold only; the backend does not classify abandonment
export const ABANDONED_AFTER_DAYS = 30

export function isAbandoned(project: Pick<Project, 'status' | 'days_since_activity'>): boolean {
  return project.status === 'active' && project.days_since_activity > ABANDONED_AFTER_DAYS
}
