'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowUpRight, Check, ChevronDown, CirclePlus, Moon, Plus, Search, Sun, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getDaysSinceTouched, getProgress, type Project, type ProjectStatus } from '@/lib/types'
import * as api from '@/lib/api'

const statusLabel: Record<ProjectStatus, string> = { activo: 'Activo', pausa: 'En pausa', idea: 'Idea', terminado: 'Terminado' }
const statusTone: Record<ProjectStatus, string> = { activo: 'status-active', pausa: 'status-paused', idea: 'status-idea', terminado: 'status-done' }

function StatusBadge({ status }: { status: ProjectStatus }) { return <span className={`status-badge ${statusTone[status]}`}>{statusLabel[status]}</span> }
function ProgressBar({ project }: { project: Project }) { const progress = getProgress(project); return <div className="progress-wrap"><div className="progress-track"><div className="progress-value" style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div> }
function daysTone(days: number) { return days < 7 ? 'fresh' : days <= 14 ? 'warm' : 'stale' }

function ProjectCard({ project, onOpen }: { project: Project; onOpen: () => void }) {
  const days = getDaysSinceTouched(project); const done = project.milestones.filter((m) => m.done).length
  return <button className="project-card" onClick={onOpen} aria-label={`Abrir ${project.name}`}>
    <div className="card-top"><div><h3>{project.name}</h3><p>{project.description}</p></div><StatusBadge status={project.status} /></div>
    <div className="progress-label"><span>Progreso</span><span>{done}/{project.milestones.length} hitos</span></div><ProgressBar project={project} />
    <div className={`touched ${daysTone(days)}`}>{days > 30 && project.status === 'activo' ? <AlertTriangle data-icon="inline-start" /> : null}<span>{days} días sin tocar</span>{days > 30 && project.status === 'activo' ? <em>Proyecto abandonado</em> : null}</div>
    <div className={`next-action ${!project.nextAction ? 'empty-action' : ''}`}><span>{project.nextAction ?? 'Sin próxima acción definida'}</span>{!project.nextAction ? <CirclePlus data-icon="inline-end" /> : <ArrowUpRight data-icon="inline-end" />}</div>
  </button>
}

function ProjectDrawer({ project, onClose, onUpdate }: { project: Project; onClose: () => void; onUpdate: (project: Project) => void }) {
  const [tab, setTab] = useState<'detalles' | 'ideas' | 'decisiones'>('detalles'); const [action, setAction] = useState(project.nextAction ?? '');
  const saveAction = async () => onUpdate(await api.setNextAction(project.id, action))
  const updateStatus = async (status: ProjectStatus) => { if (status === 'activo' && project.status !== 'activo') { const activeCount = (await api.getProjects()).filter((item) => item.status === 'activo').length; if (activeCount >= 3 && !window.confirm('Ya tienes 3 proyectos activos. Activar este proyecto puede diluir tu foco. ¿Quieres continuar?')) return } onUpdate(await api.setStatus(project.id, status)) }
  const toggle = async (milestoneId: string) => onUpdate(await api.toggleMilestone(project.id, milestoneId))
  return <aside className="drawer" aria-label={`Detalles de ${project.name}`}><div className="drawer-head"><div><p className="eyebrow">Detalle del proyecto</p><h2>{project.name}</h2></div><Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar"><X /></Button></div>
    <div className="drawer-tabs">{(['detalles', 'ideas', 'decisiones'] as const).map((item) => <button key={item} className={tab === item ? 'selected' : ''} onClick={() => setTab(item)}>{item === 'detalles' ? 'Detalles' : item === 'ideas' ? `Ideas · ${project.ideasCount}` : `Decisiones · ${project.decisionsCount}`}</button>)}</div>
    {tab === 'detalles' ? <div className="drawer-content"><p className="drawer-description">{project.description}</p><label className="field-label" htmlFor="status">Estado</label><select id="status" value={project.status} onChange={(e) => updateStatus(e.target.value as ProjectStatus)}>{Object.entries(statusLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><label className="field-label" htmlFor="next-action">Próxima acción</label><div className="action-input"><input id="next-action" value={action} onChange={(e) => setAction(e.target.value)} onBlur={saveAction} placeholder="¿Cuál es el siguiente paso?" /><Button size="sm" onClick={saveAction}>Guardar</Button></div><div className="section-title"><span>Hitos</span><span>{getProgress(project)}%</span></div><div className="milestones">{project.milestones.map((milestone) => <label key={milestone.id} className="milestone"><input type="checkbox" checked={milestone.done} onChange={() => toggle(milestone.id)} /><span className="checkmark">{milestone.done ? <Check /> : null}</span><span className={milestone.done ? 'completed' : ''}>{milestone.title}</span></label>)}</div></div> : <div className="drawer-empty"><div className="empty-icon">{tab === 'ideas' ? '✦' : '◌'}</div><h3>Aún no hay {tab}</h3><p>Este espacio se llenará cuando empieces a documentar el proyecto.</p><Button variant="outline"><Plus data-icon="inline-start" />Añadir {tab === 'ideas' ? 'idea' : 'decisión'}</Button></div>}
  </aside>
}

export default function ProjectDashboard() {
  const [projects, setProjects] = useState<Project[]>([]); const [filter, setFilter] = useState<'todos' | ProjectStatus>('todos'); const [sort, setSort] = useState('touch'); const [selected, setSelected] = useState<Project | null>(null); const [light, setLight] = useState(false); const [query, setQuery] = useState('')
  useEffect(() => { api.getProjects().then(setProjects) }, [])
  const active = projects.filter((p) => p.status === 'activo').length
  const visible = projects.filter((p) => filter === 'todos' || p.status === filter).filter((p) => p.name.toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === 'progress' ? getProgress(b) - getProgress(a) : getDaysSinceTouched(b) - getDaysSinceTouched(a))
  const focus = projects.filter((p) => p.status === 'activo')
  const update = (project: Project) => { setProjects((all) => all.map((p) => p.id === project.id ? project : p)); setSelected(project) }
  return <main className={light ? 'dashboard light' : 'dashboard'}><header className="header"><div className="brand"><div className="brand-mark">●</div><span>Kairos</span></div><div className="header-actions"><span className={`counter ${active > 3 ? 'over' : ''}`}>{active} / 3 activos</span><Button variant="ghost" size="icon" onClick={() => setLight(!light)} aria-label="Cambiar tema">{light ? <Moon /> : <Sun />}</Button></div></header>
    <div className="container"><div className="intro"><div><p className="eyebrow">Tu espacio de construcción</p><h1>Menos proyectos.<br /><span>Más terminados.</span></h1><p className="lead">Mantén el foco en lo que importa y siempre ten claro el siguiente paso.</p></div><div className="active-note"><div className="note-dot" /><div><strong>{active > 3 ? 'Demasiados proyectos activos' : 'Buen ritmo de foco'}</strong><p>{active > 3 ? 'Pausa alguno para recuperar claridad.' : 'Tienes espacio para avanzar.'}</p></div></div></div>
      {focus.length > 0 && <section className="focus-section"><div className="section-heading"><div><p className="eyebrow">Ahora mismo</p><h2>En foco</h2></div><span className="section-count">{focus.length} proyectos</span></div><div className="focus-grid">{focus.map((project) => <button key={project.id} className="focus-card" onClick={() => setSelected(project)}><div className="focus-number">0{focus.indexOf(project) + 1}</div><div className="focus-info"><StatusBadge status={project.status} /><h3>{project.name}</h3><p>{project.nextAction ?? 'Define una próxima acción para desbloquearlo'}</p></div><ArrowUpRight /></button>)}</div></section>}
      <section className="projects-section"><div className="section-heading"><div><p className="eyebrow">Vista general</p><h2>Todos tus proyectos</h2></div><div className="search"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar..." /></div></div><div className="toolbar"><div className="filters">{[['todos','Todos'],['activo','Activos'],['pausa','Pausa'],['idea','Ideas'],['terminado','Terminados']].map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value as typeof filter)}>{label}</button>)}</div><label className="sort">Ordenar por <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="touch">Días sin tocar</option><option value="progress">Progreso</option></select><ChevronDown /></label></div><div className="project-grid">{visible.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => setSelected(project)} />)}</div>{visible.length === 0 && <div className="no-results"><h3>No encontramos proyectos</h3><p>Prueba con otro filtro o término de búsqueda.</p></div>}</section>
    </div>{selected && <><div className="drawer-backdrop" onClick={() => setSelected(null)} /><ProjectDrawer project={selected} onClose={() => setSelected(null)} onUpdate={update} /></>}</main>
}
