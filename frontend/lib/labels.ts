import { ApiError } from './api'
import type { ProjectStatus } from './types'

export const statusLabel: Record<ProjectStatus, string> = {
  idea: 'Idea',
  active: 'Activo',
  paused: 'En pausa',
  done: 'Terminado',
}

// Backend details (English) that have a dedicated Spanish message
const knownDetails: Record<string, string> = {
  'Active project limit reached':
    'Ya alcanzaste el límite de proyectos activos. Pausa o termina uno antes de activar otro.',
  'next_action is required to activate':
    'Define una próxima acción antes de activar el proyecto.',
  'Project not found': 'El proyecto ya no existe.',
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return 'No se pudo conectar con el servidor. Revisa que el backend esté encendido.'
    const known = typeof error.detail === 'string' ? knownDetails[error.detail] : undefined
    if (known) return known
    if (error.status === 404) return 'No se encontró el recurso solicitado.'
    if (error.status === 409) return 'La operación entra en conflicto con el estado actual.'
    if (error.status === 422) return 'Los datos enviados no son válidos.'
    return `El servidor respondió con un error (${error.status}).`
  }
  return 'Ocurrió un error inesperado.'
}
