// Mirrors the backend schemas (snake_case, English statuses). Progress and
// days_since_activity are computed by the API and must not be recomputed here.

export const PROJECT_STATUSES = ['idea', 'active', 'paused', 'done'] as const
export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

export type Project = {
  id: number
  name: string
  slug: string
  description: string
  status: ProjectStatus
  next_action: string | null
  last_activity_at: string
  created_at: string
  progress: number
  milestones_done: number
  milestones_total: number
  days_since_activity: number
}

export type ProjectCreate = { name: string; description?: string }

// null only clears next_action; on the other fields it means "unchanged"
export type ProjectUpdate = Partial<Pick<Project, 'name' | 'description' | 'status' | 'next_action'>>

export type Milestone = {
  id: number
  project_id: number
  title: string
  done: boolean
  position: number
  completed_at: string | null
  created_at: string
}

export type MilestoneUpdate = Partial<Pick<Milestone, 'title' | 'done' | 'position'>>

export type Idea = {
  id: number
  project_id: number | null
  content: string
  created_at: string
}

export type IdeaCreate = { content: string; project_id?: number | null }

export type Decision = {
  id: number
  project_id: number
  title: string
  rationale: string
  created_at: string
}

export type DecisionCreate = { title: string; rationale: string }

export type BotCommand = { name: string; syntax: string; description: string }

export type ExportSummary = {
  projects_exported: number
  files_written: number
  files_unchanged: number
  orphans: string[]
}
