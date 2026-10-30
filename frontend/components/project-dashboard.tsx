'use client'

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ArrowUpRight, Check, ChevronDown, Moon, Plus, Search, Sun, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PROJECT_STATUSES, type Milestone, type Project, type ProjectStatus } from '@/lib/types'
import { errorMessage, statusLabel } from '@/lib/labels'
import * as api from '@/lib/api'
import { ProjectCard } from '@/components/projects/project-card'
import { StatusBadge } from '@/components/projects/status-badge'

const filterLabels: [string, string][] = [['all', 'Todos'], ['active', 'Activos'], ['paused', 'Pausa'], ['idea', 'Ideas'], ['done', 'Terminados']]

function Notice({ message, onDismiss }: { message: string; onDismiss: () => void }) { return <div className="notice" role="alert"><AlertTriangle /><span>{message}</span><button onClick={onDismiss} aria-label="Cerrar aviso"><X /></button></div> }
function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) { return <div className="state-panel" role="alert"><h3>No pudimos cargar tus proyectos</h3><p>{message}</p><Button variant="outline" onClick={onRetry}>Reintentar</Button></div> }
function EmptyProjects() { return <div className="state-panel"><h3>Aún no tienes proyectos</h3><p>Crea el primero desde el bot de Telegram con /proyecto &lt;nombre&gt;.</p></div> }
function ProjectsSkeleton() { return <div className="project-grid" aria-busy="true" aria-label="Cargando proyectos">{[0, 1, 2].map((i) => <div key={i} className="project-card skeleton" />)}</div> }


function ProjectDrawer({ project, onClose, onUpdate, onError }: { project: Project; onClose: () => void; onUpdate: (project: Project) => void; onError: (error: unknown) => void }) {
  const [tab, setTab] = useState<'detalles' | 'ideas' | 'decisiones'>('detalles'); const [action, setAction] = useState(project.next_action ?? ''); const [milestones, setMilestones] = useState<Milestone[] | null>(null)
  const projectId = project.id
  useEffect(() => { api.milestones.list(projectId).then(setMilestones).catch(onError) }, [projectId, onError])
  const saveAction = async () => { const next = action.trim() || null; if (next === project.next_action) return; try { onUpdate(await api.projects.update(project.id, { next_action: next })) } catch (error) { onError(error); setAction(project.next_action ?? '') } }
  const updateStatus = async (status: ProjectStatus) => { try { onUpdate(await api.projects.update(project.id, { status })) } catch (error) { onError(error) } }
  const toggle = async (milestone: Milestone) => { try { await api.milestones.update(milestone.id, { done: !milestone.done }); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated) } catch (error) { onError(error) } }
  return <aside className="drawer" aria-label={`Detalles de ${project.name}`}><div className="drawer-head"><div><p className="eyebrow">Detalle del proyecto</p><h2>{project.name}</h2></div><Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar"><X /></Button></div>
    <div className="drawer-tabs">{(['detalles', 'ideas', 'decisiones'] as const).map((item) => <button key={item} className={tab === item ? 'selected' : ''} onClick={() => setTab(item)}>{item === 'detalles' ? 'Detalles' : item === 'ideas' ? 'Ideas' : 'Decisiones'}</button>)}</div>
    {tab === 'detalles' ? <div className="drawer-content"><p className="drawer-description">{project.description}</p><label className="field-label" htmlFor="status">Estado</label><select id="status" value={project.status} onChange={(e) => updateStatus(e.target.value as ProjectStatus)}>{PROJECT_STATUSES.map((value) => <option key={value} value={value}>{statusLabel[value]}</option>)}</select><label className="field-label" htmlFor="next-action">Próxima acción</label><div className="action-input"><input id="next-action" value={action} onChange={(e) => setAction(e.target.value)} onBlur={saveAction} placeholder="¿Cuál es el siguiente paso?" /><Button size="sm" onClick={saveAction}>Guardar</Button></div><div className="section-title"><span>Hitos</span><span>{project.progress}%</span></div><div className="milestones">{milestones === null ? <div className="skeleton skeleton-line" aria-busy="true" /> : milestones.length === 0 ? <p className="drawer-description">Este proyecto aún no tiene hitos.</p> : milestones.map((milestone) => <label key={milestone.id} className="milestone"><input type="checkbox" checked={milestone.done} onChange={() => toggle(milestone)} /><span className="checkmark">{milestone.done ? <Check /> : null}</span><span className={milestone.done ? 'completed' : ''}>{milestone.title}</span></label>)}</div></div> : <div className="drawer-empty"><div className="empty-icon">{tab === 'ideas' ? '✦' : '◌'}</div><h3>Aún no hay {tab}</h3><p>Este espacio se llenará cuando empieces a documentar el proyecto.</p><Button variant="outline"><Plus data-icon="inline-start" />Añadir {tab === 'ideas' ? 'idea' : 'decisión'}</Button></div>}
  </aside>
}

type Load = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; projects: Project[] }

export default function ProjectDashboard() {
  const [load, setLoad] = useState<Load>({ state: 'loading' }); const [filter, setFilter] = useState('all'); const [sort, setSort] = useState('touch'); const [selectedId, setSelectedId] = useState<number | null>(null); const [light, setLight] = useState(false); const [query, setQuery] = useState(''); const [notice, setNotice] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
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
  return <main className={light ? 'dashboard light' : 'dashboard'}><header className="header"><div className="brand"><div className="brand-mark">●</div><span>Kairos</span></div><div className="header-actions">{load.state === 'ready' && <span className="counter">{active} activos</span>}<Button variant="ghost" size="icon" onClick={() => setLight(!light)} aria-label="Cambiar tema">{light ? <Moon /> : <Sun />}</Button></div></header>
    <div className="container">{notice && <Notice message={notice} onDismiss={() => setNotice(null)} />}<div className="intro"><div><p className="eyebrow">Tu espacio de construcción</p><h1>Menos proyectos.<br /><span>Más terminados.</span></h1><p className="lead">Mantén el foco en lo que importa y siempre ten claro el siguiente paso.</p></div></div>
      {load.state === 'loading' && <ProjectsSkeleton />}
      {load.state === 'error' && <LoadError message={load.message} onRetry={retry} />}
      {load.state === 'ready' && projects.length === 0 && <EmptyProjects />}
      {load.state === 'ready' && projects.length > 0 && <>
      {focus.length > 0 && <section className="focus-section"><div className="section-heading"><div><p className="eyebrow">Ahora mismo</p><h2>En foco</h2></div><span className="section-count">{focus.length} proyectos</span></div><div className="focus-grid">{focus.map((project, index) => <button key={project.id} className="focus-card" onClick={() => setSelectedId(project.id)}><div className="focus-number">0{index + 1}</div><div className="focus-info"><StatusBadge status={project.status} /><h3>{project.name}</h3><p>{project.next_action ?? 'Define una próxima acción para desbloquearlo'}</p></div><ArrowUpRight /></button>)}</div></section>}
      <section className="projects-section"><div className="section-heading"><div><p className="eyebrow">Vista general</p><h2>Todos tus proyectos</h2></div><div className="search"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar..." /></div></div><div className="toolbar"><div className="filters">{filterLabels.map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}</div><label className="sort">Ordenar por <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="touch">Días sin tocar</option><option value="progress">Progreso</option></select><ChevronDown /></label></div><div className="project-grid">{visible.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => setSelectedId(project.id)} />)}</div>{visible.length === 0 && <div className="no-results"><h3>No encontramos proyectos</h3><p>Prueba con otro filtro o término de búsqueda.</p></div>}</section></>}
    </div>{selected && <><div className="drawer-backdrop" onClick={() => setSelectedId(null)} /><ProjectDrawer key={selected.id} project={selected} onClose={() => setSelectedId(null)} onUpdate={update} onError={showError} /></>}</main>
}
