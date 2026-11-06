'use client'

import { CircleCheck, CirclePause, PowerOff, RefreshCw, TriangleAlert, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboard } from '@/components/dashboard/dashboard-context'
import { formatAgo, formatDateTime, formatTime } from '@/lib/format'
import { BOT_STATE_LABEL, botStateExplanation } from '@/lib/labels'
import type { BotState, BotStatus } from '@/lib/types'

const STATE_ICON: Record<BotState, LucideIcon> = {
  running: CircleCheck,
  failed: TriangleAlert,
  disabled: PowerOff,
  stopped: CirclePause,
}

function Facts({ status }: { status: BotStatus }) {
  const facts: [string, string][] = []
  if (status.status === 'failed' && status.reason) facts.push(['Motivo', status.reason])
  if (status.started_at) facts.push(['Iniciado', formatDateTime(status.started_at)])
  if (status.status === 'running') {
    facts.push(['Último mensaje enviado', status.last_message_sent_at ? formatDateTime(status.last_message_sent_at) : 'Ninguno todavía'])
  }
  if (status.last_error) facts.push(['Último error de conexión', `${status.last_error.type}, ${formatAgo(status.last_error.at)}`])
  if (facts.length === 0) return null
  return <dl className="bot-facts">
    {facts.map(([term, value]) => <div key={term}><dt>{term}</dt><dd>{value}</dd></div>)}
  </dl>
}

export function BotStatusCard() {
  const { botStatus } = useDashboard()
  const { data, loading, checking, error, checkedAt, check } = botStatus
  return <section className="projects-section" aria-labelledby="bot-status-title">
    <div className="section-heading metrics-heading">
      <h2 id="bot-status-title">Estado del bot</h2>
      <div className="metrics-refresh">
        {checkedAt && !loading && <span>Comprobado a las <time dateTime={checkedAt.toISOString()}>{formatTime(checkedAt)}</time></span>}
        <Button variant="outline" className="metrics-refresh-btn" onClick={check} loading={checking} loadingText="Comprobando…">
          <RefreshCw data-icon="inline-start" aria-hidden="true" />Comprobar de nuevo
        </Button>
      </div>
    </div>
    <div className="bot-status">
      {loading && <div aria-busy="true" aria-label="Comprobando el bot"><Skeleton className="h-[72px] rounded-[8px]" /></div>}
      {!loading && error && <div className="bot-status-error" role="alert">
        <p>No pudimos consultar el estado del bot.</p>
        <p className="bot-status-detail">{error}</p>
        <Button variant="outline" className="metrics-refresh-btn" onClick={check}>Reintentar</Button>
      </div>}
      {!loading && data && (() => {
        const Icon = STATE_ICON[data.status]
        return <div aria-live="polite">
          <p className="bot-state" data-state={data.status}><Icon aria-hidden="true" />{BOT_STATE_LABEL[data.status]}</p>
          <p className="bot-status-detail">{botStateExplanation(data)}</p>
          <Facts status={data} />
        </div>
      })()}
    </div>
  </section>
}
