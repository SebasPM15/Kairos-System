import { ApiError } from './api'
import { formatAgo } from './format'
import type { BotState, BotStatus, ExportSummary, ProjectStatus } from './types'

export const statusLabel: Record<ProjectStatus, string> = {
  idea: 'Idea',
  active: 'Activo',
  paused: 'En pausa',
  done: 'Terminado',
}

// Singular/plural forms per count noun. The key + count signature maps onto ICU plural messages
// when next-intl arrives, so call sites will not change.
const COUNT_FORMS = {
  day: { one: 'día', other: 'días' },
  milestone: { one: 'hito', other: 'hitos' },
  decision: { one: 'decisión', other: 'decisiones' },
  idea: { one: 'idea', other: 'ideas' },
  project: { one: 'proyecto', other: 'proyectos' },
  activeProject: { one: 'activo', other: 'activos' },
  projectExported: { one: 'proyecto exportado', other: 'proyectos exportados' },
  fileWritten: { one: 'archivo escrito', other: 'archivos escritos' },
  fileUnchanged: { one: 'sin cambios', other: 'sin cambios' },
  week: { one: 'semana', other: 'semanas' },
  alert: { one: 'alerta', other: 'alertas' },
  ideaCaptured: { one: 'idea capturada', other: 'ideas capturadas' },
  ideaAssigned: { one: 'idea asignada', other: 'ideas asignadas' },
  milestoneCompleted: { one: 'hito completado', other: 'hitos completados' },
} as const

export type CountKey = keyof typeof COUNT_FORMS

const pluralRules = new Intl.PluralRules('es')

export function pluralLabel(key: CountKey, count: number): string {
  return COUNT_FORMS[key][pluralRules.select(count) === 'one' ? 'one' : 'other']
}

export function formatCount(key: CountKey, count: number): string {
  return `${count} ${pluralLabel(key, count)}`
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

// Intentionally different: the card states a fact, the focus card nudges the user to unblock the project
export const NO_NEXT_ACTION_LABEL = 'Sin próxima acción definida'
export const NO_NEXT_ACTION_FOCUS_PROMPT = 'Define una próxima acción para desbloquearlo'

// Success toasts: short confirmations of something that already happened
export const TOAST = {
  errorTitle: 'No se pudo completar la acción',
  projectCreated: 'Proyecto creado',
  milestoneAdded: 'Hito añadido',
  decisionAdded: 'Decisión registrada',
  ideaAdded: 'Idea añadida',
  ideaAssigned: 'Idea asignada',
  ideaUnassigned: 'Idea devuelta a la bandeja',
  ideaDeleted: 'Idea borrada',
  exportDone: 'Exportación lista',
  remindersSnoozed: 'Recordatorios pospuestos',
  remindersMuted: 'Recordatorios silenciados',
  remindersReactivated: 'Recordatorios reactivados',
} as const

export function exportSummaryText(summary: ExportSummary): string {
  const projects = formatCount('projectExported', summary.projects_exported)
  const written = formatCount('fileWritten', summary.files_written)
  const unchanged = formatCount('fileUnchanged', summary.files_unchanged)
  return `${projects}; ${written} y ${unchanged}.`
}

export const BOT_STATE_LABEL: Record<BotState, string> = {
  running: 'Activo',
  disabled: 'Desactivado',
  failed: 'Con fallo',
  stopped: 'Detenido',
}

// What the user should do about the state; the backend only sends codes and exception names
export function botStateExplanation(status: BotStatus): string {
  switch (status.status) {
    case 'running':
      return 'El bot recibe tus mensajes por Telegram.'
    case 'disabled':
      return status.reason === 'missing_user_id'
        ? 'Falta definir TELEGRAM_ALLOWED_USER_ID en el archivo .env. Reinicia el backend después de cambiarlo.'
        : 'Falta definir TELEGRAM_BOT_TOKEN en el archivo .env. Reinicia el backend después de cambiarlo.'
    case 'failed':
      return 'El bot no pudo iniciar. Revisa el token y la conexión, y reinicia el backend.'
    case 'stopped':
      return 'El bot se detuvo. Reinicia el backend para volver a activarlo.'
  }
}

// Banner text: a failed start, or a running bot whose connection is failing right now
export function botDownMessage(status: BotStatus): string {
  if (status.status === 'failed') {
    const cause = status.reason ? ` (${status.reason})` : ''
    return `El bot de Telegram no está funcionando${cause}. Mientras siga así no recibirás mensajes ni recordatorios.`
  }
  const error = status.last_error
  const cause = error ? ` (${error.type}, ${formatAgo(error.at)})` : ''
  return `El bot de Telegram perdió la conexión${cause}. Sigue intentando reconectar; los recordatorios pueden retrasarse.`
}
