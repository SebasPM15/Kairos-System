// "2026-11-02" is a calendar day, not an instant: building it from parts keeps it out of UTC conversions
function parseDay(day: string): Date {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(year, month - 1, date)
}

export function formatWeekStart(day: string): string {
  return parseDay(day).toLocaleDateString('es', { day: 'numeric', month: 'short' }).replace('.', '')
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

const relative = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })

// "hace 5 minutos"; the unit is the largest one that fits
export function formatAgo(iso: string, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return 'hace unos segundos'
  if (seconds < 3600) return relative.format(-Math.floor(seconds / 60), 'minute')
  if (seconds < 86400) return relative.format(-Math.floor(seconds / 3600), 'hour')
  return relative.format(-Math.floor(seconds / 86400), 'day')
}
