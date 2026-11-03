'use client'

import { useCallback, useSyncExternalStore } from 'react'
import { THEME_KEY, type Theme } from './theme'

// The class on <html> is the single source of truth; the inline script sets it before hydration
function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  return () => observer.disconnect()
}

const getSnapshot = (): Theme => document.documentElement.classList.contains('light') ? 'light' : 'dark'
const getServerSnapshot = (): Theme => 'dark'

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const setTheme = useCallback((next: Theme) => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(next)
    root.style.colorScheme = next
    try { localStorage.setItem(THEME_KEY, next) } catch { /* storage blocked: the choice lasts until reload */ }
  }, [])

  return { theme, setTheme }
}
