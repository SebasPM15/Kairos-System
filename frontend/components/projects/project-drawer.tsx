'use client'

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PROJECT_STATUSES, type Decision, type DecisionCreate, type Idea, type Milestone, type Project, type ProjectStatus } from '@/lib/types'
import { statusLabel } from '@/lib/labels'
import * as api from '@/lib/api'
import { DecisionList } from './decision-list'
import { DecisionForm } from './decision-form'
import { IdeaList } from './idea-list'
import { MilestoneForm } from './milestone-form'
import { MilestoneList } from './milestone-list'

export interface ProjectDrawerProps {
  project: Project
  onClose: () => void
  onUpdate: (project: Project) => void
  onError: (error: unknown) => void
}

type Tab = 'detalles' | 'ideas' | 'decisiones'
const TABS: [Tab, string][] = [['detalles', 'Detalles'], ['ideas', 'Ideas'], ['decisiones', 'Decisiones']]

export function ProjectDrawer({ project, onClose, onUpdate, onError }: ProjectDrawerProps) {
  const [tab, setTab] = useState<Tab>('detalles')
  const [action, setAction] = useState(project.next_action ?? '')
  const [milestones, setMilestones] = useState<Milestone[] | null>(null)
  const [ideas, setIdeas] = useState<Idea[] | null>(null)
  const [decisions, setDecisions] = useState<Decision[] | null>(null)
  const projectId = project.id

  useEffect(() => {
    api.milestones.list(projectId).then(setMilestones).catch(onError)
    api.ideas.listByProject(projectId).then(setIdeas).catch(onError)
    api.decisions.listByProject(projectId).then(setDecisions).catch(onError)
  }, [projectId, onError])

  const saveAction = async () => { const next = action.trim() || null; if (next === project.next_action) return; try { onUpdate(await api.projects.update(project.id, { next_action: next })) } catch (error) { onError(error); setAction(project.next_action ?? '') } }
  const updateStatus = async (status: ProjectStatus) => { try { onUpdate(await api.projects.update(project.id, { status })) } catch (error) { onError(error) } }
  // The backend owns the percentage, so refresh the project after every toggle
  const toggle = async (milestone: Milestone) => { try { await api.milestones.update(milestone.id, { done: !milestone.done }); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated) } catch (error) { onError(error) } }

  const addMilestone = async (title: string) => { await api.milestones.create(project.id, title); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated) }

  const addDecision = async (data: DecisionCreate) => { await api.decisions.create(project.id, data); setDecisions(await api.decisions.listByProject(project.id)); onUpdate(await api.projects.get(project.id)) }

  return <aside className="drawer" aria-label={`Detalles de ${project.name}`}><div className="drawer-head"><div><p className="eyebrow">Detalle del proyecto</p><h2>{project.name}</h2></div><Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar"><X /></Button></div>
    <div className="drawer-tabs">{TABS.map(([value, label]) => <button key={value} className={tab === value ? 'selected' : ''} onClick={() => setTab(value)}>{label}</button>)}</div>
    {tab === 'detalles' && <div className="drawer-content"><p className="drawer-description">{project.description}</p><label className="field-label" htmlFor="status">Estado</label><select id="status" value={project.status} onChange={(e) => updateStatus(e.target.value as ProjectStatus)}>{PROJECT_STATUSES.map((value) => <option key={value} value={value}>{statusLabel[value]}</option>)}</select><label className="field-label" htmlFor="next-action">Próxima acción</label><div className="action-input"><input id="next-action" value={action} onChange={(e) => setAction(e.target.value)} onBlur={saveAction} placeholder="¿Cuál es el siguiente paso?" /><Button size="sm" onClick={saveAction}>Guardar</Button></div><div className="section-title"><span>Hitos</span><span>{project.progress}%</span></div><div className="milestones"><MilestoneList milestones={milestones} onToggle={toggle} /></div><MilestoneForm onSubmit={addMilestone} onError={onError} /></div>}
    {tab === 'ideas' && <div className="drawer-content"><IdeaList ideas={ideas} /></div>}
    {tab === 'decisiones' && <div className="drawer-content"><DecisionForm onSubmit={addDecision} onError={onError} /><DecisionList decisions={decisions} /></div>}
  </aside>
}
