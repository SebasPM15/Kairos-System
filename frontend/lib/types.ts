export type ProjectStatus = 'idea' | 'activo' | 'pausa' | 'terminado'

export type Milestone = { id: string; title: string; done: boolean }

export type Project = {
  id: string
  name: string
  description: string
  status: ProjectStatus
  lastTouchedAt: string
  nextAction: string | null
  milestones: Milestone[]
  ideasCount: number
  decisionsCount: number
}

export function getProgress(project: Project) {
  if (!project.milestones.length) return 0
  return Math.round((project.milestones.filter((milestone) => milestone.done).length / project.milestones.length) * 100)
}

export function getDaysSinceTouched(project: Project) {
  return Math.max(0, Math.floor((Date.now() - new Date(project.lastTouchedAt).getTime()) / 86400000))
}
