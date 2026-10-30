import { ApiError } from './api'
import type { ProjectStatus } from './types'

export const statusLabel: Record<ProjectStatus, string> = {
  idea: 'Idea',
  active: 'Activo',
  paused: 'En pausa',
  done: 'Terminado',
}

export type ErrorContext = { maxActive?: number }

export function activeLimitMessage(maxActive?: number) {
  const limit = maxActive === undefined ? 'el límite' : `el máximo de ${maxActive}`
  return `Ya alcanzaste ${limit} de proyectos activos. Pausa o termina uno antes de activar otro.`
}

export const NEXT_ACTION_REQUIRED_MESSAGE = 'Define una próxima acción antes de activar el proyecto.'

// Messages keyed by status + route; the backend's detail text is only a last resort
function specificMessage(error: ApiError, context: ErrorContext): string | undefined {
  const key = `${error.status} ${error.endpoint}`
  switch (key) {
    case '409 PATCH /projects/:id':
      return activeLimitMessage(context.maxActive)
    case '422 PATCH /projects/:id':
      return error.kind === 'business' ? NEXT_ACTION_REQUIRED_MESSAGE : undefined
    case '409 POST /export':
      return 'No se pudo exportar: revisa la configuración del vault de Obsidian.'
  }
}

export function errorMessage(error: unknown, context: ErrorContext = {}): string {
  if (!(error instanceof ApiError)) return 'Ocurrió un error inesperado.'
  if (error.kind === 'network') return 'No se pudo conectar con el servidor. Revisa que el backend esté encendido.'
  const specific = specificMessage(error, context)
  if (specific) return specific
  if (error.status >= 500) return 'El servidor falló. Inténtalo de nuevo en un momento.'
  if (error.status === 404) return 'No se encontró el recurso. Puede que ya se haya eliminado.'
  if (error.kind === 'validation') return 'Hay datos que no son válidos. Revisa los campos marcados.'
  if (error.kind === 'business') return String(error.detail)
  return `El servidor respondió con un error (${error.status}).`
}

const issueMessages: Record<string, string> = {
  string_too_short: 'Este campo no puede estar vacío.',
  string_too_long: 'El texto es demasiado largo.',
  missing: 'Este campo es obligatorio.',
}

// Maps Pydantic issues to Spanish messages by field name (last element of `loc`)
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {}
  const result: Record<string, string> = {}
  for (const issue of error.issues) {
    const field = String(issue.loc[issue.loc.length - 1])
    result[field] ??= issueMessages[issue.type] ?? 'Valor no válido.'
  }
  return result
}
