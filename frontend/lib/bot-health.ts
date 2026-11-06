import type { BotStatus } from './types'

// While an outage lasts PTB keeps calling error_callback, so a newer error means it is still down
export const RECENT_ERROR_MS = 5 * 60 * 1000

export function hasRecentError(status: BotStatus, now: number = Date.now()): boolean {
  return status.last_error !== null && now - new Date(status.last_error.at).getTime() <= RECENT_ERROR_MS
}

// The banner shows for a failed start or for a running bot that is failing right now; a bot that is
// disabled on purpose (no token configured) never counts as down.
export function isBotDown(status: BotStatus | null, now: number = Date.now()): boolean {
  if (!status) return false
  return status.status === 'failed' || (status.status === 'running' && hasRecentError(status, now))
}
