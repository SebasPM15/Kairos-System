'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Reminders } from './types'
import { errorMessage } from './labels'
import * as api from './api'

export const REMINDERS_TTL_MS = 60_000

export interface RemindersState {
  data: Reminders | null
  // First fetch, nothing to show yet
  loading: boolean
  // A fetch while older data stays on screen
  refreshing: boolean
  // The last fetch failed; data from an earlier one may still be there
  error: string | null
}

export interface RemindersCache extends RemindersState {
  // Used by the block while it is on screen: fetches now if needed and refetches after every mutation
  watch: () => () => void
  refresh: () => void
}

const EMPTY: RemindersState = { data: null, loading: false, refreshing: false, error: null }

// Lazy cache for GET /reminders. Alerts depend on any project, milestone, idea or decision change, so
// every successful mutation marks it stale; while the block is mounted the refetch happens right away.
export function useRemindersCache(): RemindersCache {
  const [state, setState] = useState<RemindersState>(EMPTY)
  const stale = useRef(false)
  const inFlight = useRef(false)
  const fetchedAt = useRef<number | null>(null)
  const watching = useRef(0)
  // The request's own callback needs to start the next one, and a hook cannot reference itself
  const again = useRef<() => void>(() => undefined)

  const fetchNow = useCallback(() => {
    if (inFlight.current) return
    inFlight.current = true
    stale.current = false
    setState((s) => ({ ...s, loading: s.data === null, refreshing: s.data !== null, error: null }))
    api.reminders.list().then(
      (data) => {
        fetchedAt.current = Date.now()
        setState({ data, loading: false, refreshing: false, error: null })
      },
      (error) => setState((s) => ({ ...s, loading: false, refreshing: false, error: errorMessage(error) })),
    ).finally(() => {
      inFlight.current = false
      // A mutation landed while the request was out: that answer may predate it
      if (stale.current && watching.current > 0) again.current()
    })
  }, [])

  useEffect(() => { again.current = fetchNow }, [fetchNow])

  useEffect(() => api.onMutation(() => {
    stale.current = true
    if (watching.current > 0) fetchNow()
  }), [fetchNow])

  const watch = useCallback(() => {
    watching.current += 1
    const age = fetchedAt.current === null ? Infinity : Date.now() - fetchedAt.current
    if (age > REMINDERS_TTL_MS || stale.current) fetchNow()
    return () => { watching.current -= 1 }
  }, [fetchNow])

  return { ...state, watch, refresh: fetchNow }
}
