'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import type { ExportDialogProps } from '@/components/export/export-dialog'
import type { DeleteIdeaDialogProps } from '@/components/ideas/delete-idea-dialog'
import type { ProjectDrawerProps } from '@/components/projects/project-drawer'
import { useDashboard } from './dashboard-context'

// Dialogs are out of the first-load bundle: each chunk is fetched the first time its dialog opens
// (or earlier, when the trigger is hovered or focused) and the dialog then stays mounted, so
// the exit animation and focus return work as with an eagerly loaded one.
const loaders = {
  create: () => import('./create-project-dialog').then((m) => m.CreateProjectDialog),
  export: () => import('@/components/export/export-dialog').then((m) => m.ExportDialog),
  menu: () => import('./mobile-nav').then((m) => m.MobileNav),
  drawer: () => import('@/components/projects/project-drawer').then((m) => m.ProjectDrawer),
  deleteIdea: () => import('@/components/ideas/delete-idea-dialog').then((m) => m.DeleteIdeaDialog),
}

export type LazyDialog = keyof typeof loaders

export function preloadDialog(name: LazyDialog): void {
  void loaders[name]()
}

const CreateProjectDialog = dynamic(loaders.create, { ssr: false })
const ExportDialog = dynamic(loaders.export, { ssr: false })
const MobileNav = dynamic(loaders.menu, { ssr: false })
const ProjectDrawer = dynamic(loaders.drawer, { ssr: false })
const DeleteIdeaDialog = dynamic(loaders.deleteIdea, { ssr: false })

// True from the first time `open` is true onwards
function useOpenedOnce(open: boolean): boolean {
  const [opened, setOpened] = useState(false)
  if (open && !opened) setOpened(true)
  return opened
}

export function LazyCreateProjectDialog() {
  const { creating } = useDashboard()
  return useOpenedOnce(creating) ? <CreateProjectDialog /> : null
}

export function LazyExportDialog(props: ExportDialogProps) {
  return useOpenedOnce(props.open) ? <ExportDialog {...props} /> : null
}

export function LazyMobileNav(props: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return useOpenedOnce(props.open) ? <MobileNav {...props} /> : null
}

// Rendered only while there is a project, so it is born on the first opening
export function LazyProjectDrawer(props: ProjectDrawerProps) {
  return <ProjectDrawer {...props} />
}

export function LazyDeleteIdeaDialog(props: DeleteIdeaDialogProps) {
  return useOpenedOnce(props.idea !== null) ? <DeleteIdeaDialog {...props} /> : null
}
