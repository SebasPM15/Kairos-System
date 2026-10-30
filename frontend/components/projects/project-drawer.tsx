'use client'

import { useEffect, useState } from 'react'
import { Check, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { PROJECT_STATUSES, type Milestone, type Project, type ProjectStatus } from '@/lib/types'
import { statusLabel } from '@/lib/labels'
import * as api from '@/lib/api'

export interface ProjectDrawerProps {
  project: Project
  onClose: () => void
  onUpdate: (project: Project) => void
  onError: (error: unknown) => void
}

export function ProjectDrawer({ project, onClose, onUpdate, onError }: ProjectDrawerProps) {
  const [tab, setTab] = useState<'detalles' | 'ideas' | 'decisiones'>('detalles'); const [action, setAction] = useState(project.next_action ?? ''); const [milestones, setMilestones] = useState<Milestone[] | null>(null)
  const projectId = project.id
  useEffect(() => { api.milestones.list(projectId).then(setMilestones).catch(onError) }, [projectId, onError])
  const saveAction = async () => { const next = action.trim() || null; if (next === project.next_action) return; try { onUpdate(await api.projects.update(project.id, { next_action: next })) } catch (error) { onError(error); setAction(project.next_action ?? '') } }
  const updateStatus = async (status: ProjectStatus) => { try { onUpdate(await api.projects.update(project.id, { status })) } catch (error) { onError(error) } }
  const toggle = async (milestone: Milestone) => { try { await api.milestones.update(milestone.id, { done: !milestone.done }); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated) } catch (error) { onError(error) } }
  return <aside className="drawer" aria-label={`Detalles de ${project.name}`}><div className="drawer-head"><div><p className="eyebrow">Detalle del proyecto</p><h2>{project.name}</h2></div><Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar"><X /></Button></div>
    <div className="drawer-tabs">{(['detalles', 'ideas', 'decisiones'] as const).map((item) => <button key={item} className={tab === item ? 'selected' : ''} onClick={() => setTab(item)}>{item === 'detalles' ? 'Detalles' : item === 'ideas' ? 'Ideas' : 'Decisiones'}</button>)}</div>
    {tab === 'detalles' ? <div className="drawer-content"><p className="drawer-description">{project.description}</p><label className="field-label" htmlFor="status">Estado</label><select id="status" value={project.status} onChange={(e) => updateStatus(e.target.value as ProjectStatus)}>{PROJECT_STATUSES.map((value) => <option key={value} value={value}>{statusLabel[value]}</option>)}</select><label className="field-label" htmlFor="next-action">Próxima acción</label><div className="action-input"><input id="next-action" value={action} onChange={(e) => setAction(e.target.value)} onBlur={saveAction} placeholder="¿Cuál es el siguiente paso?" /><Button size="sm" onClick={saveAction}>Guardar</Button></div><div className="section-title"><span>Hitos</span><span>{project.progress}%</span></div><div className="milestones">{milestones === null ? <Skeleton className="h-[38px] rounded-[7px]" aria-busy="true" /> : milestones.length === 0 ? <p className="drawer-description">Este proyecto aún no tiene hitos.</p> : milestones.map((milestone) => <label key={milestone.id} className="milestone"><input type="checkbox" checked={milestone.done} onChange={() => toggle(milestone)} /><span className="checkmark">{milestone.done ? <Check /> : null}</span><span className={milestone.done ? 'completed' : ''}>{milestone.title}</span></label>)}</div></div> : <div className="drawer-empty"><div className="empty-icon">{tab === 'ideas' ? '✦' : '◌'}</div><h3>Aún no hay {tab}</h3><p>Este espacio se llenará cuando empieces a documentar el proyecto.</p><Button variant="outline"><Plus data-icon="inline-start" />Añadir {tab === 'ideas' ? 'idea' : 'decisión'}</Button></div>}
  </aside>
}
