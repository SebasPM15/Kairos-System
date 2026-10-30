import type {
  BotCommand,
  Decision,
  DecisionCreate,
  ExportSummary,
  Idea,
  IdeaCreate,
  Milestone,
  MilestoneUpdate,
  Project,
  ProjectCreate,
  PublicConfig,
  ProjectUpdate,
} from './types'

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

// Pydantic validation error as returned by FastAPI on 422
export type ValidationIssue = { loc: (string | number)[]; msg: string; type: string }

export type ErrorKind = 'network' | 'business' | 'validation' | 'unknown'

export class ApiError extends Error {
  constructor(
    // 0 when the request never reached the server
    readonly status: number,
    // FastAPI's `detail`: a string for domain errors, a list for Pydantic validation
    readonly detail: unknown,
    // Route template such as "PATCH /projects/:id"; messages are keyed by it
    readonly endpoint: string,
  ) {
    super(typeof detail === 'string' ? detail : `API error ${status}`)
    this.name = 'ApiError'
  }

  get kind(): ErrorKind {
    if (this.status === 0) return 'network'
    if (typeof this.detail === 'string') return 'business'
    return Array.isArray(this.detail) ? 'validation' : 'unknown'
  }

  get issues(): ValidationIssue[] {
    return this.kind === 'validation' ? (this.detail as ValidationIssue[]) : []
  }
}

function routeOf(method: string, path: string) {
  return `${method} ${path.replace(/\/\d+(?=\/|$)/g, '/:id')}`
}

async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = init.method ?? 'GET'
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: init.body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: 'no-store',
    })
  } catch {
    throw new ApiError(0, null, routeOf(method, path))
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(response.status, payload?.detail ?? null, routeOf(method, path))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const projects = {
  list: () => request<Project[]>('/projects'),
  get: (id: number) => request<Project>(`/projects/${id}`),
  create: (data: ProjectCreate) => request<Project>('/projects', { method: 'POST', body: data }),
  update: (id: number, data: ProjectUpdate) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: data }),
  remove: (id: number) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
}

export const milestones = {
  list: (projectId: number) => request<Milestone[]>(`/projects/${projectId}/milestones`),
  create: (projectId: number, title: string) =>
    request<Milestone>(`/projects/${projectId}/milestones`, { method: 'POST', body: { title } }),
  update: (id: number, data: MilestoneUpdate) =>
    request<Milestone>(`/milestones/${id}`, { method: 'PATCH', body: data }),
  remove: (id: number) => request<void>(`/milestones/${id}`, { method: 'DELETE' }),
}

export const ideas = {
  inbox: () => request<Idea[]>('/ideas'),
  listByProject: (projectId: number) => request<Idea[]>(`/projects/${projectId}/ideas`),
  create: (data: IdeaCreate) => request<Idea>('/ideas', { method: 'POST', body: data }),
  createInProject: (projectId: number, content: string) =>
    request<Idea>(`/projects/${projectId}/ideas`, { method: 'POST', body: { content } }),
  // projectId null returns the idea to the inbox
  assign: (id: number, projectId: number | null) =>
    request<Idea>(`/ideas/${id}`, { method: 'PATCH', body: { project_id: projectId } }),
  remove: (id: number) => request<void>(`/ideas/${id}`, { method: 'DELETE' }),
}

export const decisions = {
  listByProject: (projectId: number) => request<Decision[]>(`/projects/${projectId}/decisions`),
  create: (projectId: number, data: DecisionCreate) =>
    request<Decision>(`/projects/${projectId}/decisions`, { method: 'POST', body: data }),
  remove: (id: number) => request<void>(`/decisions/${id}`, { method: 'DELETE' }),
}

export const bot = {
  commands: () => request<BotCommand[]>('/bot/commands'),
}

export const vault = {
  export: () => request<ExportSummary>('/export', { method: 'POST' }),
}

export const getConfig = () => request<PublicConfig>('/config')
