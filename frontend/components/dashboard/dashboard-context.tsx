'use client'

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Project, ProjectCreate } from '@/lib/types'
import { TOAST, errorMessage } from '@/lib/labels'
import { toast } from '@/components/ui/toaster'
import * as api from '@/lib/api'

export type View = 'projects' | 'ideas' | 'bot'

export type Load =
  | { state: 'loading' }
  | { state: 'error'; message: string }
  | { state: 'ready'; projects: Project[] }

// Shared dashboard state. It lives above the views so that switching view (or, later, route)
// keeps the project list, the open drawer and the project filters.
export interface DashboardContextValue {
  load: Load
  projects: Project[]
  activeCount: number
  // Null until /config answers; the counter then falls back to "N activos"
  maxActive: number | null
  retry: () => void
  // Silent refetch: keeps the current list on screen instead of flashing the skeleton
  refreshProjects: () => void
  createProject: (data: ProjectCreate) => Promise<void>
  updateProject: (project: Project) => void

  notice: string | null
  setNotice: (message: string | null) => void
  showError: (error: unknown) => void

  view: View
  changeView: (view: View) => void
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

const DashboardContext = createContext<DashboardContextValue | null>(null)

export function useDashboard(): DashboardContextValue {
  const value = useContext(DashboardContext)
  if (!value) throw new Error('useDashboard must be used inside DashboardProvider')
  return value
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [load, setLoad] = useState<Load>({ state: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [maxActive, setMaxActive] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [view, setView] = useState<View>('projects')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('touch')
  const [query, setQuery] = useState('')

  useEffect(() => {
    api.getConfig().then((config) => setMaxActive(config.max_active_projects), () => undefined)
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

  const showError = useCallback((error: unknown) => setNotice(errorMessage(error)), [])

  const createProject = async (data: ProjectCreate) => {
    const project = await api.projects.create(data)
    setNotice(null)
    setLoad((current) => current.state === 'ready'
      ? { state: 'ready', projects: [...current.projects, project] }
      : current)
    setCreating(false)
    toast.success(TOAST.projectCreated, project.name)
  }

  const updateProject = (project: Project) => {
    setNotice(null)
    setLoad((current) => current.state === 'ready'
      ? { state: 'ready', projects: current.projects.map((p) => p.id === project.id ? project : p) }
      : current)
  }

  const changeView = (next: View) => { setView(next); setSelectedId(null) }

  const projects = load.state === 'ready' ? load.projects : []
  const selected = projects.find((p) => p.id === selectedId) ?? null
  const activeCount = projects.filter((p) => p.status === 'active').length

  return <DashboardContext.Provider value={{
    load, projects, activeCount, maxActive, retry, refreshProjects, createProject, updateProject,
    notice, setNotice, showError,
    view, changeView, selectedId, selected, setSelectedId,
    creating, setCreating, exporting, setExporting,
    filter, setFilter, sort, setSort, query, setQuery,
  }}>{children}</DashboardContext.Provider>
}
