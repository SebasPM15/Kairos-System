'use client'

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ArrowUpRight, ChevronDown, Moon, Search, Sun, X } from 'lucide-react'
import { Alert, AlertAction, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Project } from '@/lib/types'
import { NO_NEXT_ACTION_FOCUS_PROMPT, errorMessage } from '@/lib/labels'
import * as api from '@/lib/api'
import { ProjectDrawer } from '@/components/projects/project-drawer'
import { ProjectList } from '@/components/projects/project-list'
import { StatusBadge } from '@/components/projects/status-badge'

const filterLabels: [string, string][] = [['all', 'Todos'], ['active', 'Activos'], ['paused', 'Pausa'], ['idea', 'Ideas'], ['done', 'Terminados']]

function Notice({ message, onDismiss }: { message: string; onDismiss: () => void }) { return <Alert variant="destructive" className="mb-7"><AlertTriangle /><AlertDescription className="text-destructive">{message}</AlertDescription><AlertAction><button onClick={onDismiss} aria-label="Cerrar aviso"><X className="size-3.5" /></button></AlertAction></Alert> }
function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) { return <div className="state-panel" role="alert"><h3>No pudimos cargar tus proyectos</h3><p>{message}</p><Button variant="outline" onClick={onRetry}>Reintentar</Button></div> }
function EmptyProjects() { return <div className="state-panel"><h3>Aún no tienes proyectos</h3><p>Crea el primero desde el bot de Telegram con /proyecto &lt;nombre&gt;.</p></div> }
function ProjectsSkeleton() { return <div className="project-grid" aria-busy="true" aria-label="Cargando proyectos">{[0, 1, 2].map((i) => <Skeleton key={i} className="project-card min-h-[230px]" />)}</div> }


type Load = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; projects: Project[] }

export default function ProjectDashboard() {
  const [load, setLoad] = useState<Load>({ state: 'loading' }); const [filter, setFilter] = useState('all'); const [sort, setSort] = useState('touch'); const [selectedId, setSelectedId] = useState<number | null>(null); const [light, setLight] = useState(false); const [query, setQuery] = useState(''); const [notice, setNotice] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0); const [maxActive, setMaxActive] = useState<number | null>(null)
  // Without the limit the counter falls back to "N activos"
  useEffect(() => { api.getConfig().then((config) => setMaxActive(config.max_active_projects), () => undefined) }, [attempt])
  useEffect(() => {
    let live = true
    api.projects.list().then((projects) => live && setLoad({ state: 'ready', projects }), (error) => live && setLoad({ state: 'error', message: errorMessage(error) }))
    return () => { live = false }
  }, [attempt])
  const retry = () => { setLoad({ state: 'loading' }); setAttempt((n) => n + 1) }
  const showError = useCallback((error: unknown) => setNotice(errorMessage(error)), [])
  const projects = load.state === 'ready' ? load.projects : []
  const selected = projects.find((p) => p.id === selectedId) ?? null
  const active = projects.filter((p) => p.status === 'active').length
  const visible = projects.filter((p) => filter === 'all' || p.status === filter).filter((p) => p.name.toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === 'progress' ? b.progress - a.progress : b.days_since_activity - a.days_since_activity)
  const focus = projects.filter((p) => p.status === 'active')
  const update = (project: Project) => { setNotice(null); setLoad((current) => current.state === 'ready' ? { state: 'ready', projects: current.projects.map((p) => p.id === project.id ? project : p) } : current) }
  return <main className={light ? 'dashboard light' : 'dashboard'}><header className="header"><div className="brand"><div className="brand-mark">●</div><span>Kairos</span></div><div className="header-actions">{load.state === 'ready' && <span className="counter">{maxActive === null ? active : `${active} / ${maxActive}`} activos</span>}<Button variant="ghost" size="icon" onClick={() => setLight(!light)} aria-label="Cambiar tema">{light ? <Moon /> : <Sun />}</Button></div></header>
    <div className="container">{notice && <Notice message={notice} onDismiss={() => setNotice(null)} />}<div className="intro"><div><p className="eyebrow">Tu espacio de construcción</p><h1>Menos proyectos.<br /><span>Más terminados.</span></h1><p className="lead">Mantén el foco en lo que importa y siempre ten claro el siguiente paso.</p></div></div>
      {load.state === 'loading' && <ProjectsSkeleton />}
      {load.state === 'error' && <LoadError message={load.message} onRetry={retry} />}
      {load.state === 'ready' && projects.length === 0 && <EmptyProjects />}
      {load.state === 'ready' && projects.length > 0 && <>
      {focus.length > 0 && <section className="focus-section"><div className="section-heading"><div><p className="eyebrow">Ahora mismo</p><h2>En foco</h2></div><span className="section-count">{focus.length} proyectos</span></div><div className="focus-grid">{focus.map((project, index) => <button key={project.id} className="focus-card" onClick={() => setSelectedId(project.id)}><div className="focus-number">0{index + 1}</div><div className="focus-info"><StatusBadge status={project.status} /><h3>{project.name}</h3><p>{project.next_action ?? NO_NEXT_ACTION_FOCUS_PROMPT}</p></div><ArrowUpRight /></button>)}</div></section>}
      <section className="projects-section"><div className="section-heading"><div><p className="eyebrow">Vista general</p><h2>Todos tus proyectos</h2></div><div className="search"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar..." /></div></div><div className="toolbar"><div className="filters">{filterLabels.map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}</div><label className="sort">Ordenar por <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="touch">Días sin tocar</option><option value="progress">Progreso</option></select><ChevronDown /></label></div><ProjectList projects={visible} onOpen={setSelectedId} /></section></>}
    </div>{selected && <><div className="drawer-backdrop" onClick={() => setSelectedId(null)} /><ProjectDrawer key={selected.id} project={selected} onClose={() => setSelectedId(null)} onUpdate={update} onError={showError} /></>}</main>
}
