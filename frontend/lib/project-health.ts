import type { Project, StaleAfterDays } from './types'

export type DaysTone = 'fresh' | 'warm' | 'stale'

type Health = Pick<Project, 'status' | 'days_since_activity'>

// The thresholds live in the backend (GET /config); idea and done projects never go stale
function thresholdFor(status: Project['status'], stale: StaleAfterDays): number | null {
  if (status === 'active') return stale.active
  if (status === 'paused') return stale.paused
  return null
}

// Same rule as the backend's reminders: idle for at least the threshold of its status
export function isStale(project: Health, stale: StaleAfterDays | null): boolean {
  const limit = stale ? thresholdFor(project.status, stale) : null
  return limit !== null && project.days_since_activity >= limit
}

// Presentation only: warm from half of the threshold, stale from the threshold itself
export function daysTone(project: Health, stale: StaleAfterDays | null): DaysTone {
  const limit = stale ? thresholdFor(project.status, stale) : null
  if (limit === null) return 'fresh'
  if (project.days_since_activity >= limit) return 'stale'
  return project.days_since_activity >= Math.ceil(limit / 2) ? 'warm' : 'fresh'
}
