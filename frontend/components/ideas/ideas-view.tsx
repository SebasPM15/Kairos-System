'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Idea, Project } from '@/lib/types'
import { errorMessage } from '@/lib/labels'
import { formatDate } from '@/lib/format'
import * as api from '@/lib/api'
import { IdeaForm } from '@/components/projects/idea-form'

export interface IdeasViewProps {
  // Names for the project label and the filter; may be empty if the projects failed to load
  projects: Project[]
  // Assigning to a project touches its last activity, so the project list must be refetched
  onProjectsChanged: () => void
  // For errors without a place of their own (network, 5xx)
  onError: (error: unknown) => void
}

type Load = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; ideas: Idea[] }

export const INBOX_LABEL = 'Bandeja'
const ALL = 'all'
const INBOX = 'inbox'

export function IdeasView({ projects, onProjectsChanged, onError }: IdeasViewProps) {
  const [load, setLoad] = useState<Load>({ state: 'loading' })
  const [filter, setFilter] = useState(ALL)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let live = true
    api.ideas.all().then((ideas) => live && setLoad({ state: 'ready', ideas }), (error) => live && setLoad({ state: 'error', message: errorMessage(error) }))
    return () => { live = false }
  }, [attempt])

  const retry = () => { setLoad({ state: 'loading' }); setAttempt((n) => n + 1) }
  const projectName = (id: number | null) => id === null ? INBOX_LABEL : projects.find((p) => p.id === id)?.name ?? `Proyecto ${id}`
  const add = async (content: string) => {
    const idea = await api.ideas.create({ content })
    setLoad((current) => current.state === 'ready' ? { state: 'ready', ideas: [idea, ...current.ideas] } : current)
  }

  const assign = async (idea: Idea, value: string) => {
    try {
      const updated = await api.ideas.assign(idea.id, value === INBOX ? null : Number(value))
      setLoad((current) => current.state === 'ready' ? { state: 'ready', ideas: current.ideas.map((i) => i.id === updated.id ? updated : i) } : current)
      onProjectsChanged()
    } catch (error) { onError(error) }
  }

  const ideas = load.state === 'ready' ? load.ideas : []
  const visible = ideas.filter((idea) => filter === ALL || (filter === INBOX ? idea.project_id === null : idea.project_id === Number(filter)))

  return <section className="projects-section"><div className="section-heading"><div><p className="eyebrow">Todo lo que se te ocurre</p><h2>Ideas</h2></div>
    <label className="sort">Mostrar <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filtrar ideas"><option value={ALL}>Todas</option><option value={INBOX}>Sin proyecto</option>{projects.map((p) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}</select></label></div>
    <p className="drawer-description">Las ideas nuevas van a la bandeja, sin proyecto. Después puedes asignarlas a uno.</p>
    <IdeaForm onSubmit={add} onError={onError} placeholder="Nueva idea para la bandeja" />
    {load.state === 'loading' && <div className="entries mt-4" aria-busy="true" aria-label="Cargando ideas">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-[62px] rounded-[8px]" />)}</div>}
    {load.state === 'error' && <div className="state-panel" role="alert"><h3>No pudimos cargar tus ideas</h3><p>{load.message}</p><Button variant="outline" onClick={retry}>Reintentar</Button></div>}
    {load.state === 'ready' && ideas.length === 0 && <div className="state-panel"><h3>Aún no tienes ideas</h3><p>Anótalas aquí o con /idea en el bot de Telegram.</p></div>}
    {load.state === 'ready' && ideas.length > 0 && visible.length === 0 && <div className="state-panel"><h3>No hay ideas con este filtro</h3><p>Prueba con otro proyecto o con «Todas».</p></div>}
    {visible.length > 0 && <ul className="entries mt-4">{visible.map((idea) => <li key={idea.id}><p>{idea.content}</p><div className="idea-meta"><span className={idea.project_id === null ? 'idea-tag inbox' : 'idea-tag'}>{projectName(idea.project_id)}</span><time dateTime={idea.created_at}>{formatDate(idea.created_at)}</time><select value={idea.project_id === null ? INBOX : String(idea.project_id)} onChange={(e) => assign(idea, e.target.value)} aria-label={`Proyecto de la idea ${idea.id}`}><option value={INBOX}>{INBOX_LABEL}</option>{projects.map((p) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}</select></div></li>)}</ul>}
  </section>
}
