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

export type BotCommand = { name: string; args: string; syntax: string; description: string }

export type BotState = 'disabled' | 'running' | 'failed' | 'stopped'

// reason is a code (missing_token, missing_user_id) or an exception class name, never a message
export type BotStatus = {
  status: BotState
  reason: string | null
  started_at: string | null
  last_message_sent_at: string | null
  last_error: { type: string; at: string } | null
}

export type ExportSummary = {
  projects_exported: number
  files_written: number
  files_unchanged: number
  orphans: string[]
}

// Days without activity after which a project of that status counts as stalled; the backend owns them
export type StaleAfterDays = { active: number; paused: number }

export type PublicConfig = { max_active_projects: number; stale_after_days: StaleAfterDays }

export type WeekCount = { week_start: string; count: number }

export type ProjectProgress = {
  id: number
  name: string
  status: ProjectStatus
  progress: number
  milestones_done: number
  milestones_total: number
  days_since_activity: number
}

export type Metrics = {
  generated_at: string
  timezone: string
  weeks: number
  // Monday of the current, still partial, week; it is the last entry of every weekly series
  current_week_start: string
  projects_by_status: { status: ProjectStatus; count: number }[]
  project_progress: ProjectProgress[]
  milestones_completed: WeekCount[]
  ideas_captured: WeekCount[]
  ideas_assigned: WeekCount[]
  idea_totals: { captured: number; in_inbox: number; assigned: number }
}
