'use client'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboard } from './dashboard-context'
import { FocusSection } from './focus-section'
import { ProjectsSection } from './projects-section'

function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="state-panel" role="alert">
    <h3>No pudimos cargar tus proyectos</h3>
    <p>{message}</p>
    <Button variant="outline" onClick={onRetry}>Reintentar</Button>
  </div>
}

function EmptyProjects() {
  return <div className="state-panel">
    <h3>Aún no tienes proyectos</h3>
    <p>Crea el primero desde el bot de Telegram con /proyecto &lt;nombre&gt;.</p>
  </div>
}

function ProjectsSkeleton() {
  return <div className="project-grid" aria-busy="true" aria-label="Cargando proyectos">
    {[0, 1, 2].map((i) => <Skeleton key={i} className="project-card min-h-[230px]" />)}
  </div>
}

function Intro() {
  return <div className="intro"><div>
    <p className="eyebrow">Tu espacio de construcción</p>
    <h1>Menos proyectos.<br /><span>Más terminados.</span></h1>
    <p className="lead">Mantén el foco en lo que importa y siempre ten claro el siguiente paso.</p>
  </div></div>
}

export function ProjectsView() {
  const { load, projects, retry } = useDashboard()
  return <>
    <Intro />
    {load.state === 'loading' && <ProjectsSkeleton />}
    {load.state === 'error' && <LoadError message={load.message} onRetry={retry} />}
    {load.state === 'ready' && projects.length === 0 && <EmptyProjects />}
    {load.state === 'ready' && projects.length > 0 && <>
      <FocusSection />
      <ProjectsSection />
    </>}
  </>
}
