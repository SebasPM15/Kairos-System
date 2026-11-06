'use client'

import Link from 'next/link'
import { RefreshCw, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { isBotDown } from '@/lib/bot-health'
import { botDownMessage } from '@/lib/labels'
import { ROUTES, useDashboard } from './dashboard-context'

// Persistent: it stays until the bot is back, because fixing it (token, duplicate instance, restart) is
// the user's job. A toast would vanish and must never carry the only way to solve a problem.
export function BotBanner() {
  const { botStatus, view } = useDashboard()
  const { data, checking, check } = botStatus
  if (!data || !isBotDown(data)) return null
  return <div className="banner-wrap">
    <div className="bot-banner" role="alert">
      <TriangleAlert aria-hidden="true" />
      <p>{botDownMessage(data)}</p>
      <div className="bot-banner-actions">
        {view !== 'bot' && <Link className="metrics-link" href={ROUTES.bot}>Ver detalles</Link>}
        <Button variant="outline" className="metrics-refresh-btn" onClick={check} loading={checking} loadingText="Comprobando…">
          <RefreshCw data-icon="inline-start" aria-hidden="true" />Comprobar de nuevo
        </Button>
      </div>
    </div>
  </div>
}
