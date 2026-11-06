'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { BotStatus } from './types'
import { errorMessage } from './labels'
import * as api from './api'

export const BOT_STATUS_POLL_MS = 60_000
// A focus or visibility event right after a fetch would only repeat it
const MIN_GAP_MS = 5_000

export interface BotStatusCache {
  // The last successful answer; null while loading and after a failed check, because then the state is unknown
  data: BotStatus | null
  // First check, nothing to show yet
  loading: boolean
  // A check while an earlier answer stays on screen
  checking: boolean
  error: string | null
  checkedAt: Date | null
  check: () => void
}

// One shared check of GET /bot/status for the banner and the Bot tab: every minute while the tab is
// visible, and again when the window regains focus.
export function useBotStatus(): BotStatusCache {
  const [data, setData] = useState<BotStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const inFlight = useRef(false)
  const lastStart = useRef(0)

  const check = useCallback(() => {
    if (inFlight.current) return
    inFlight.current = true
    lastStart.current = Date.now()
    setChecking(true)
    api.bot.status().then(
      (status) => { setData(status); setError(null) },
      (failure) => { setData(null); setError(errorMessage(failure)) },
    ).finally(() => {
      inFlight.current = false
      setLoading(false)
      setChecking(false)
      setCheckedAt(new Date())
    })
  }, [])

  useEffect(() => {
    check()
    const visible = () => document.visibilityState === 'visible'
    const poll = window.setInterval(() => { if (visible()) check() }, BOT_STATUS_POLL_MS)
    const refocus = () => { if (visible() && Date.now() - lastStart.current > MIN_GAP_MS) check() }
    window.addEventListener('focus', refocus)
    document.addEventListener('visibilitychange', refocus)
    return () => {
      window.clearInterval(poll)
      window.removeEventListener('focus', refocus)
      document.removeEventListener('visibilitychange', refocus)
    }
  }, [check])

  return { data, loading, checking, error, checkedAt, check }
}
