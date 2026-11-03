'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { PROJECT_STATUSES, type Decision, type DecisionCreate, type Idea, type Milestone, type Project, type ProjectStatus, type ProjectUpdate } from '@/lib/types'
import { TOAST, errorMessage, fieldErrors, statusLabel } from '@/lib/labels'
import { toast } from '@/components/ui/toaster'
import * as api from '@/lib/api'
import { DecisionList } from './decision-list'
import { DecisionForm } from './decision-form'
import { IdeaForm } from './idea-form'
import { IdeaList } from './idea-list'
import { MilestoneForm } from './milestone-form'
import { MilestoneList } from './milestone-list'

export interface ProjectDrawerProps {
  project: Project
  open: boolean
  onClose: () => void
  onUpdate: (project: Project) => void
  // Real limit from /config; undefined until it loads
  maxActive?: number
  // Only for errors without a place of their own (network, 5xx)
  onError: (error: unknown) => void
}

type Tab = 'detalles' | 'ideas' | 'decisiones'
const TABS: [Tab, string][] = [['detalles', 'Detalles'], ['ideas', 'Ideas'], ['decisiones', 'Decisiones']]

export function ProjectDrawer({ project, open, maxActive, onClose, onUpdate, onError }: ProjectDrawerProps) {
  const [tab, setTab] = useState<Tab>('detalles')
  const [action, setAction] = useState(project.next_action ?? '')
  const [milestones, setMilestones] = useState<Milestone[] | null>(null)
  const [ideas, setIdeas] = useState<Idea[] | null>(null)
  const [decisions, setDecisions] = useState<Decision[] | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [actionError, setActionError] = useState<string | null>(null)
  const projectId = project.id

  // Loading problems stay inside the drawer with a retry; they are not toasts
  useEffect(() => {
    const failed = (error: unknown) => setLoadError(errorMessage(error))
    api.milestones.list(projectId).then(setMilestones).catch(failed)
    api.ideas.listByProject(projectId).then(setIdeas).catch(failed)
    api.decisions.listByProject(projectId).then(setDecisions).catch(failed)
  }, [projectId, attempt])

  const retryLoad = () => { setLoadError(null); setAttempt((n) => n + 1) }

  // 409 belongs to the status control, business/validation 422 to the next-action field
  const reportProjectError = (error: unknown) => {
    if (error instanceof api.ApiError) {
      if (error.status === 409) return setStatusError(errorMessage(error, { maxActive }))
      if (error.status === 422) {
        if (error.kind === 'business') return setActionError(errorMessage(error))
        const fields = fieldErrors(error)
        if (fields.next_action) return setActionError(fields.next_action)
        if (fields.status) return setStatusError(fields.status)
      }
    }
    onError(error)
  }
  const patchProject = async (data: ProjectUpdate) => { setStatusError(null); setActionError(null); try { onUpdate(await api.projects.update(project.id, data)); return true } catch (error) { reportProjectError(error); return false } }
  const saveAction = async () => { const next = action.trim() || null; if (next === project.next_action) return; if (!(await patchProject({ next_action: next }))) setAction(project.next_action ?? '') }
  const updateStatus = (status: ProjectStatus) => patchProject({ status })
  // The backend owns the percentage, so refresh the project after every toggle
  const toggle = async (milestone: Milestone) => { try { await api.milestones.update(milestone.id, { done: !milestone.done }); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated) } catch (error) { onError(error) } }

  const addMilestone = async (title: string) => { await api.milestones.create(project.id, title); const [fresh, updated] = await Promise.all([api.milestones.list(project.id), api.projects.get(project.id)]); setMilestones(fresh); onUpdate(updated); toast.success(TOAST.milestoneAdded) }

  const addIdea = async (content: string) => { await api.ideas.createInProject(project.id, content); setIdeas(await api.ideas.listByProject(project.id)); onUpdate(await api.projects.get(project.id)); toast.success(TOAST.ideaAdded) }

  const addDecision = async (data: DecisionCreate) => { await api.decisions.create(project.id, data); setDecisions(await api.decisions.listByProject(project.id)); onUpdate(await api.projects.get(project.id)); toast.success(TOAST.decisionAdded) }

  return <Dialog open={open} onOpenChange={(next) => { if (!next) onClose() }}><DialogContent variant="side" eyebrow="Detalle del proyecto" title={project.name}>
    {loadError && <div className="state-panel" role="alert"><h3>No pudimos cargar los datos del proyecto</h3><p>{loadError}</p><Button variant="outline" onClick={retryLoad}>Reintentar</Button></div>}
    <div className="drawer-tabs">{TABS.map(([value, label]) => <button key={value} className={tab === value ? 'selected' : ''} onClick={() => setTab(value)}>{label}</button>)}</div>
    {tab === 'detalles' && <div className="drawer-content"><p className="drawer-description">{project.description}</p><label className="field-label" htmlFor="status">Estado</label><Select id="status" value={project.status} onChange={(e) => updateStatus(e.target.value as ProjectStatus)}>{PROJECT_STATUSES.map((value) => <option key={value} value={value}>{statusLabel[value]}</option>)}</Select>{statusError && <p className="field-error" role="alert">{statusError}</p>}<Field label="Próxima acción" error={actionError}><div className="action-input"><Input value={action} onChange={(e) => setAction(e.target.value)} onBlur={saveAction} placeholder="¿Cuál es el siguiente paso?" /><Button size="sm" onClick={saveAction}>Guardar</Button></div></Field><div className="section-title"><span>Hitos</span><span>{project.progress}%</span></div><div className="milestones"><MilestoneList milestones={milestones} onToggle={toggle} /></div><MilestoneForm onSubmit={addMilestone} onError={onError} /></div>}
    {tab === 'ideas' && <div className="drawer-content"><IdeaForm onSubmit={addIdea} onError={onError} autoFocus /><IdeaList ideas={ideas} /></div>}
    {tab === 'decisiones' && <div className="drawer-content"><DecisionForm onSubmit={addDecision} onError={onError} /><DecisionList decisions={decisions} /></div>}
  </DialogContent></Dialog>
}
