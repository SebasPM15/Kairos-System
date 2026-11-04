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
