'use client'

import { IdeasView } from '@/components/ideas/ideas-view'
import { useDashboard } from './dashboard-context'

export function IdeasRoute() {
  const { projects, refreshProjects, showError } = useDashboard()
  return <IdeasView projects={projects} onProjectsChanged={refreshProjects} onError={showError} />
}
