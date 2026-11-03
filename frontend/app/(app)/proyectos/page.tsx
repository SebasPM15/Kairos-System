import type { Metadata } from 'next'
import { ProjectsView } from '@/components/dashboard/projects-view'

export const metadata: Metadata = { title: 'Proyectos · Kairos' }

export default function Page() {
  return <ProjectsView />
}
