'use client'

import { useState, type ReactNode } from 'react'
import { Menu, Plus, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { pluralLabel } from '@/lib/labels'
import type { Project } from '@/lib/types'
import { ExportDialog } from '@/components/export/export-dialog'
import { ProjectDrawer } from '@/components/projects/project-drawer'
import { useDashboard } from './dashboard-context'
import { MobileNav } from './mobile-nav'
import { Sidebar, SidebarBrand } from './sidebar'
import { CreateProjectDialog } from './create-project-dialog'

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

function HeaderActions() {
  const { exporting, setExporting } = useDashboard()
  return <div className="header-actions">
    <Button variant="outline" size="sm" onClick={() => setExporting(!exporting)} aria-expanded={exporting}>
      <Upload className="export-icon" /><span className="btn-label">Exportar a Obsidian</span>
    </Button>
    <ProjectActions />
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

// Sidebar, header with the actions, the page, the project drawer and the creation and export dialogs
export function AppShell({ children }: { children: ReactNode }) {
  const { exporting, setExporting } = useDashboard()
  const [navOpen, setNavOpen] = useState(false)
  return <div className="dashboard">
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <Sidebar />
    <div className="dashboard-main">
      <header className="header">
        <Button variant="ghost" size="icon" className="menu-button" aria-label="Abrir menú" aria-expanded={navOpen} aria-controls="mobile-nav" onClick={() => setNavOpen(true)}>
          <Menu />
        </Button>
        <div className="header-brand"><SidebarBrand /></div>
        <HeaderActions />
      </header>
      <main id="contenido" tabIndex={-1}>
        <div className="container">{children}</div>
      </main>
    </div>
    <MobileNav open={navOpen} onOpenChange={setNavOpen} />
    <SelectedProjectDrawer />
    <CreateProjectDialog />
    <ExportDialog open={exporting} onOpenChange={setExporting} />
  </div>
}
