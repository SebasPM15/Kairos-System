'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Metrics } from './types'
import { errorMessage } from './labels'
import * as api from './api'

export const METRICS_TTL_MS = 60_000

export interface MetricsState {
  data: Metrics | null
  // When the data on screen was fetched
  fetchedAt: Date | null
  // First fetch, nothing to show yet
  loading: boolean
  // A fetch while older data stays on screen
  refreshing: boolean
  // The last fetch failed; data from an earlier one may still be there
  error: string | null
}

export interface MetricsCache extends MetricsState {
  // Called when the page mounts: fetches when empty, invalidated or older than a minute
  ensure: () => void
  // The «Actualizar» button: always fetches
  refresh: () => void
}

const EMPTY: MetricsState = { data: null, fetchedAt: null, loading: false, refreshing: false, error: null }

// Lazy cache for GET /metrics. Any successful mutation marks it stale; the next visit refetches.
export function useMetricsCache(): MetricsCache {
  const [state, setState] = useState<MetricsState>(EMPTY)
  const stale = useRef(false)
  const inFlight = useRef(false)
  const fetchedAt = useRef<number | null>(null)
  // The request's own callback needs to start the next one, and a hook cannot reference itself
  const again = useRef<() => void>(() => undefined)

  const fetchNow = useCallback(() => {
    if (inFlight.current) return
    inFlight.current = true
    stale.current = false
    setState((s) => ({ ...s, loading: s.data === null, refreshing: s.data !== null, error: null }))
    api.metrics.get().then(
      (data) => {
        const now = new Date()
        fetchedAt.current = now.getTime()
        setState({ data, fetchedAt: now, loading: false, refreshing: false, error: null })
      },
      (error) => setState((s) => ({ ...s, loading: false, refreshing: false, error: errorMessage(error) })),
    ).finally(() => {
      inFlight.current = false
      // A mutation landed while the request was out: that answer may predate it
      if (stale.current) again.current()
    })
  }, [])

  useEffect(() => { again.current = fetchNow }, [fetchNow])

  useEffect(() => api.onMutation(() => { stale.current = true }), [])

  const ensure = useCallback(() => {
    const age = fetchedAt.current === null ? Infinity : Date.now() - fetchedAt.current
    if (age > METRICS_TTL_MS || stale.current) fetchNow()
  }, [fetchNow])

  return { ...state, ensure, refresh: fetchNow }
}
