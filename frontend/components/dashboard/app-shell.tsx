'use client'

import { useState, type ReactNode } from 'react'
import { Moon, Plus, Sun, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { pluralLabel } from '@/lib/labels'
import type { Project } from '@/lib/types'
import { ExportDialog } from '@/components/export/export-dialog'
import { ProjectDrawer } from '@/components/projects/project-drawer'
import { useDashboard, type View } from './dashboard-context'
import { CreateProjectDialog } from './create-project-dialog'
import { Notice } from './notice'

const VIEWS: [View, string][] = [['projects', 'Proyectos'], ['ideas', 'Ideas'], ['bot', 'Bot']]

function MainNav() {
  const { view, changeView } = useDashboard()
  return <nav className="main-nav" aria-label="Secciones">
    {VIEWS.map(([value, label]) => <button
      key={value}
      className={view === value ? 'selected' : ''}
      aria-current={view === value ? 'page' : undefined}
      onClick={() => changeView(value)}
    >{label}</button>)}
  </nav>
}

function ProjectActions() {
  const { load, view, maxActive, activeCount, setCreating } = useDashboard()
  if (view !== 'projects' || load.state !== 'ready') return null
  const counter = maxActive === null ? activeCount : `${activeCount} / ${maxActive}`
  return <>
    <Button variant="outline" size="sm" onClick={() => setCreating(true)}>
      <Plus data-icon="inline-start" /><span className="btn-label">Nuevo proyecto</span>
    </Button>
    <span className="counter">{counter} {pluralLabel('activeProject', maxActive ?? activeCount)}</span>
  </>
}

function HeaderActions({ light, onToggleTheme }: { light: boolean; onToggleTheme: () => void }) {
  const { exporting, setExporting } = useDashboard()
  return <div className="header-actions">
    <Button variant="outline" size="sm" onClick={() => setExporting(!exporting)} aria-expanded={exporting}>
      <Upload className="export-icon" /><span className="btn-label">Exportar a Obsidian</span>
    </Button>
    <ProjectActions />
    <Button variant="ghost" size="icon" onClick={onToggleTheme} aria-label="Cambiar tema">
      {light ? <Moon /> : <Sun />}
    </Button>
  </div>
}

function SelectedProjectDrawer() {
  const { selected, maxActive, setSelectedId, updateProject, showError } = useDashboard()
  // Keep the last project mounted while the panel slides out
  const [last, setLast] = useState<Project | null>(null)
  if (selected && selected !== last) setLast(selected)
  const project = selected ?? last
  if (!project) return null
  return <ProjectDrawer
    key={project.id}
    project={project}
    open={selected !== null}
    maxActive={maxActive ?? undefined}
    onClose={() => setSelectedId(null)}
    onUpdate={updateProject}
    onError={showError}
  />
}

// Header, notices, export panel and the project drawer; the current view is passed as children
export function AppShell({ children }: { children: ReactNode }) {
  const [light, setLight] = useState(false)
  const { notice, setNotice, exporting, setExporting } = useDashboard()
  return <main className={light ? 'dashboard light' : 'dashboard'}>
    <header className="header">
      <div className="brand"><div className="brand-mark">●</div><span>Kairos</span></div>
      <MainNav />
      <HeaderActions light={light} onToggleTheme={() => setLight(!light)} />
    </header>
    <div className="container">
      {notice && <Notice message={notice} onDismiss={() => setNotice(null)} />}
      {children}
    </div>
    <SelectedProjectDrawer />
    <CreateProjectDialog />
    <ExportDialog open={exporting} onOpenChange={setExporting} />
  </main>
}
