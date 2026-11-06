'use client'

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'
import type { Project, ProjectCreate, PublicConfig, StaleAfterDays } from '@/lib/types'
import { TOAST, errorMessage } from '@/lib/labels'
import { toast } from '@/components/ui/toaster'
import { useBotStatus, type BotStatusCache } from '@/lib/use-bot-status'
import { useMetricsCache, type MetricsCache } from '@/lib/use-metrics'
import { useRemindersCache, type RemindersCache } from '@/lib/use-reminders'
import * as api from '@/lib/api'

export type View = 'projects' | 'ideas' | 'metrics' | 'bot'

export type Load =
  | { state: 'loading' }
  | { state: 'error'; message: string }
  | { state: 'ready'; projects: Project[] }

// Shared dashboard state. The provider lives in the (app) layout, so navigating between routes
// keeps the project list, the project filters and the search text; the drawer closes on navigation.
export interface DashboardContextValue {
  load: Load
  projects: Project[]
  activeCount: number
  // Null until /config answers; the counter then falls back to "N activos"
  maxActive: number | null
  // Thresholds for "Sin avance", also from /config; null until it answers
  staleAfterDays: StaleAfterDays | null
  retry: () => void
  // Silent refetch: keeps the current list on screen instead of flashing the skeleton
  refreshProjects: () => void
  createProject: (data: ProjectCreate) => Promise<void>
  updateProject: (project: Project) => void
  metrics: MetricsCache
  botStatus: BotStatusCache
  reminders: RemindersCache

  // Mutation failures (create, assign, delete...) surface as an error toast; the form keeps what was typed
  showError: (error: unknown) => void

  // Derived from the URL
  view: View
  selectedId: number | null
  selected: Project | null
  setSelectedId: (id: number | null) => void
  creating: boolean
  setCreating: (creating: boolean) => void
  exporting: boolean
  setExporting: (exporting: boolean) => void

  filter: string
  setFilter: (filter: string) => void
  sort: string
  setSort: (sort: string) => void
  query: string
  setQuery: (query: string) => void
}

export const ROUTES: Record<View, string> = { projects: '/proyectos', ideas: '/ideas', metrics: '/metricas', bot: '/bot' }

function viewFromPath(pathname: string): View {
  if (pathname.startsWith(ROUTES.ideas)) return 'ideas'
  if (pathname.startsWith(ROUTES.metrics)) return 'metrics'
  if (pathname.startsWith(ROUTES.bot)) return 'bot'
  return 'projects'
}

const DashboardContext = createContext<DashboardContextValue | null>(null)

export function useDashboard(): DashboardContextValue {
  const value = useContext(DashboardContext)
  if (!value) throw new Error('useDashboard must be used inside DashboardProvider')
  return value
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [load, setLoad] = useState<Load>({ state: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const pathname = usePathname()
  const view = viewFromPath(pathname)
  // The selection remembers the route it was made on, so it dies when the route changes
  const [selection, setSelection] = useState<{ id: number; path: string } | null>(null)
  if (selection && selection.path !== pathname) setSelection(null)
  const selectedId = selection ? selection.id : null
  const setSelectedId = useCallback((id: number | null) => setSelection(id === null ? null : { id, path: pathname }), [pathname])
  const [creating, setCreating] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('touch')
  const [query, setQuery] = useState('')
  const metrics = useMetricsCache()
  const botStatus = useBotStatus()
  const reminders = useRemindersCache()

  useEffect(() => {
    api.getConfig().then(setConfig, () => undefined)
  }, [attempt])

  useEffect(() => {
    let live = true
    api.projects.list().then(
      (projects) => live && setLoad({ state: 'ready', projects }),
      (error) => live && setLoad({ state: 'error', message: errorMessage(error) }),
    )
    return () => { live = false }
  }, [attempt])

  const retry = () => { setLoad({ state: 'loading' }); setAttempt((n) => n + 1) }

  const refreshProjects = useCallback(() => {
    api.projects.list().then((projects) => setLoad({ state: 'ready', projects }), () => undefined)
  }, [])

  const showError = useCallback((error: unknown) => toast.error(TOAST.errorTitle, errorMessage(error)), [])

  const createProject = async (data: ProjectCreate) => {
    const project = await api.projects.create(data)
    setLoad((current) => current.state === 'ready'
      ? { state: 'ready', projects: [...current.projects, project] }
      : current)
    setCreating(false)
    toast.success(TOAST.projectCreated, project.name)
  }

  const updateProject = (project: Project) => {
    setLoad((current) => current.state === 'ready'
      ? { state: 'ready', projects: current.projects.map((p) => p.id === project.id ? project : p) }
      : current)
  }

  const maxActive = config?.max_active_projects ?? null
  const staleAfterDays = config?.stale_after_days ?? null
  const projects = load.state === 'ready' ? load.projects : []
  const selected = projects.find((p) => p.id === selectedId) ?? null
  const activeCount = projects.filter((p) => p.status === 'active').length

  return <DashboardContext.Provider value={{
    load, projects, activeCount, maxActive, staleAfterDays, retry, refreshProjects, createProject, updateProject, metrics, botStatus, reminders,
    showError,
    view, selectedId, selected, setSelectedId,
    creating, setCreating, exporting, setExporting,
    filter, setFilter, sort, setSort, query, setQuery,
  }}>{children}</DashboardContext.Provider>
}
