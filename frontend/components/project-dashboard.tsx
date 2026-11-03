'use client'

import { BotCommands } from '@/components/bot/bot-commands'
import { AppShell } from '@/components/dashboard/app-shell'
import { DashboardProvider, useDashboard } from '@/components/dashboard/dashboard-context'
import { ProjectsView } from '@/components/dashboard/projects-view'
import { IdeasView } from '@/components/ideas/ideas-view'

function CurrentView() {
  const { view, projects, refreshProjects, showError } = useDashboard()
  if (view === 'ideas') return <IdeasView projects={projects} onProjectsChanged={refreshProjects} onError={showError} />
  if (view === 'bot') return <BotCommands />
  return <ProjectsView />
}

export default function ProjectDashboard() {
  return <DashboardProvider>
    <AppShell><CurrentView /></AppShell>
  </DashboardProvider>
}
